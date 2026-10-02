import os
import json
import uuid
import datetime
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

# File Paths for Hotel Database
BOOKINGS_FILE = "bookings.json"
SERVICES_FILE = "service_requests.json"
ROOMS_FILE = "rooms.json"
FAQ_FILE = "receptionist_faq.json"

# Room numbers mapping by type
ROOM_RANGES = {
    "deluxe": ["201", "202", "203", "204", "205", "206", "207", "208"],
    "suite": ["301", "302", "303", "304", "305", "306"],
    "penthouse": ["1501", "1502"]
}

# Load Hotel FAQ / Directory Information
def load_hotel_data():
    try:
        with open(FAQ_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading FAQ file: {e}")
        return {}

HOTEL_DATA = load_hotel_data()

# Helper functions for state files
def load_state(filepath, default_value=None):
    if default_value is None:
        default_value = []
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return default_value

def save_state(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

# Room Rack Initialization & Sync
def get_rooms():
    rooms = load_state(ROOMS_FILE, None)
    if not rooms:
        rooms = [
            { "room_number": "201", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "available", "current_guest": None, "cleanliness": "clean" },
            { "room_number": "202", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "reserved", "current_guest": "David Miller", "cleanliness": "clean" },
            { "room_number": "203", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "available", "current_guest": None, "cleanliness": "clean" },
            { "room_number": "204", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "occupied", "current_guest": "Elena Rostova", "cleanliness": "clean" },
            { "room_number": "205", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "cleaning", "current_guest": None, "cleanliness": "in_progress" },
            { "room_number": "206", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "available", "current_guest": None, "cleanliness": "clean" },
            { "room_number": "301", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "occupied", "current_guest": "Sarah Jenkins", "cleanliness": "clean" },
            { "room_number": "302", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "available", "current_guest": None, "cleanliness": "clean" },
            { "room_number": "303", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "available", "current_guest": None, "cleanliness": "clean" },
            { "room_number": "304", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "cleaning", "current_guest": None, "cleanliness": "in_progress" },
            { "room_number": "1501", "room_type": "penthouse", "name": "Presidential Ocean Penthouse", "floor": 15, "status": "occupied", "current_guest": "Carlos Mendez", "cleanliness": "clean" },
            { "room_number": "1502", "room_type": "penthouse", "name": "Presidential Sky Penthouse", "floor": 15, "status": "available", "current_guest": None, "cleanliness": "clean" }
        ]
        save_state(ROOMS_FILE, rooms)
    return rooms

def save_rooms(rooms):
    save_state(ROOMS_FILE, rooms)

def sync_room_status(room_number, new_status, guest_name=None, cleanliness=None):
    rooms = get_rooms()
    for r in rooms:
        if str(r.get("room_number")) == str(room_number):
            r["status"] = new_status
            if guest_name is not None:
                r["current_guest"] = guest_name
            elif new_status in ["available", "cleaning"]:
                r["current_guest"] = None
            if cleanliness:
                r["cleanliness"] = cleanliness
            break
    save_rooms(rooms)

def calculate_stats():
    rooms = get_rooms()
    bookings = load_state(BOOKINGS_FILE)
    services = load_state(SERVICES_FILE)
    
    total_rooms = len(rooms)
    occupied_count = sum(1 for r in rooms if r.get("status") == "occupied")
    occupancy_pct = int((occupied_count / total_rooms) * 100) if total_rooms else 0
    
    in_house_guests = sum(1 for b in bookings if b.get("status") == "Checked-In")
    pending_services = sum(1 for s in services if s.get("status") in ["Pending", "Dispatched", "In-Progress"])
    total_revenue = sum(b.get("total_price", 0) for b in bookings if b.get("status") in ["Confirmed", "Checked-In", "Checked-Out"])
    
    return {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_count,
        "occupancy_pct": occupancy_pct,
        "in_house_guests": in_house_guests,
        "pending_services": pending_services,
        "total_revenue": total_revenue
    }

# Core Hotel Tools

def book_room(guest_name, room_type, checkin_date, checkout_date):
    """
    Autonomously reserves a room for a guest.
    """
    bookings = load_state(BOOKINGS_FILE)
    rooms = get_rooms()
    
    rt_lower = room_type.lower()
    matched_rt = "deluxe"
    price_per_night = 150
    room_name = "Deluxe Ocean Balcony"
    
    for rt in HOTEL_DATA.get("room_types", []):
        if rt["id"] in rt_lower or rt_lower in rt["id"] or rt["name"].lower() in rt_lower:
            matched_rt = rt["id"]
            price_per_night = rt["price_per_night"]
            room_name = rt["name"]
            break
            
    # Calculate nights
    try:
        d1 = datetime.datetime.strptime(checkin_date.strip(), "%Y-%m-%d")
        d2 = datetime.datetime.strptime(checkout_date.strip(), "%Y-%m-%d")
        nights = max(1, (d2 - d1).days)
    except Exception:
        nights = 2
        d1 = datetime.datetime.now()
        d2 = d1 + datetime.timedelta(days=2)
        checkin_date = d1.strftime("%Y-%m-%d")
        checkout_date = d2.strftime("%Y-%m-%d")
        
    total_price = nights * price_per_night
    
    # Assign room from inventory
    assigned_room = None
    for r in rooms:
        if r.get("room_type") == matched_rt and r.get("status") == "available":
            assigned_room = r.get("room_number")
            r["status"] = "reserved"
            r["current_guest"] = guest_name
            break
            
    if not assigned_room:
        for r in rooms:
            if r.get("room_type") == matched_rt and r.get("status") != "occupied":
                assigned_room = r.get("room_number")
                r["status"] = "reserved"
                r["current_guest"] = guest_name
                break
                
    if not assigned_room:
        assigned_room = ROOM_RANGES.get(matched_rt, ["201"])[0]
        
    save_rooms(rooms)
    
    booking_id = f"RGI-{uuid.uuid4().hex[:4].upper()}"
    new_booking = {
        "booking_id": booking_id,
        "guest_name": guest_name,
        "room_type": matched_rt,
        "room_name": room_name,
        "room_number": str(assigned_room),
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "nights": nights,
        "total_price": total_price,
        "status": "Confirmed",
        "key_pass_id": None,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    bookings.append(new_booking)
    save_state(BOOKINGS_FILE, bookings)
    
    widget_data = {
        "type": "booking_confirmation",
        "booking_id": booking_id,
        "guest_name": guest_name,
        "room_name": room_name,
        "room_number": str(assigned_room),
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "nights": nights,
        "price_per_night": price_per_night,
        "total_price": total_price
    }
    
    return {
        "success": True,
        "booking_id": booking_id,
        "room_number": str(assigned_room),
        "total_price": total_price,
        "widget": widget_data,
        "message": f"Successfully reserved {room_name} (Room {assigned_room}) for {guest_name} from {checkin_date} to {checkout_date} ({nights} nights). Total: ${total_price}. Booking Reference: {booking_id}."
    }

def check_in_guest(guest_identifier):
    """
    Autonomously checks in a guest using their name or reservation reference.
    Issues digital NFC room keycard and elevator directions.
    """
    bookings = load_state(BOOKINGS_FILE)
    clean_id = guest_identifier.strip().lower()
    
    matched_booking = None
    for b in bookings:
        b_id = b.get("booking_id", "").lower()
        g_name = b.get("guest_name", "").lower()
        r_num = str(b.get("room_number", ""))
        if clean_id in b_id or clean_id in g_name or g_name in clean_id or clean_id == r_num:
            matched_booking = b
            break
            
    if not matched_booking:
        return {
            "success": False,
            "message": f"No reservation was found matching '{guest_identifier}'. Please verify your name or booking confirmation number, or I can immediately create a walk-in booking for you!"
        }
        
    if matched_booking.get("status") == "Checked-In":
        room_num = matched_booking.get("room_number")
        key_id = matched_booking.get("key_pass_id") or f"KEY-{room_num}-{uuid.uuid4().hex[:4].upper()}"
        return {
            "success": True,
            "already_checked_in": True,
            "widget": {
                "type": "keycard",
                "guest_name": matched_booking.get("guest_name"),
                "room_number": str(room_num),
                "room_name": matched_booking.get("room_name", "Luxury Suite"),
                "floor": 15 if int(room_num) > 1000 else (3 if int(room_num) >= 300 else 2),
                "key_pass_id": key_id,
                "wifi_network": "Royal_Grand_Free_WiFi",
                "wifi_pass": "BEACH_LUXURY_2026",
                "checkin_date": matched_booking.get("checkin_date"),
                "checkout_date": matched_booking.get("checkout_date"),
                "checkout_time": "11:00 AM",
                "status": "Active"
            },
            "message": f"Welcome back, {matched_booking.get('guest_name')}! You are already checked into Room {room_num}. Here is your Digital Room Keycard pass. The elevators are to your right."
        }
        
    # Mark Checked-In
    matched_booking["status"] = "Checked-In"
    matched_booking["checked_in_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    room_num = str(matched_booking.get("room_number"))
    key_pass_id = f"KEY-{room_num}-{uuid.uuid4().hex[:4].upper()}"
    matched_booking["key_pass_id"] = key_pass_id
    save_state(BOOKINGS_FILE, bookings)
    
    # Update Room Rack
    floor = 15 if int(room_num) > 1000 else (3 if int(room_num) >= 300 else 2)
    sync_room_status(room_num, "occupied", guest_name=matched_booking.get("guest_name"), cleanliness="clean")
    
    widget_data = {
        "type": "keycard",
        "guest_name": matched_booking.get("guest_name"),
        "room_number": room_num,
        "room_name": matched_booking.get("room_name", "Luxury Room"),
        "floor": floor,
        "key_pass_id": key_pass_id,
        "wifi_network": "Royal_Grand_Free_WiFi",
        "wifi_pass": "BEACH_LUXURY_2026",
        "checkin_date": matched_booking.get("checkin_date"),
        "checkout_date": matched_booking.get("checkout_date"),
        "checkout_time": "11:00 AM",
        "status": "Active"
    }
    
    return {
        "success": True,
        "guest_name": matched_booking.get("guest_name"),
        "room_number": room_num,
        "key_pass_id": key_pass_id,
        "widget": widget_data,
        "message": f"Welcome to Royal Grand Inn, {matched_booking.get('guest_name')}! You are officially checked in to Room {room_num} (Floor {floor}). I have issued your secure Digital NFC Keycard pass below. Take the central elevators to Floor {floor}. Enjoy your stay with us!"
    }

def check_out_guest(room_or_guest):
    """
    Autonomously checks out a guest, settles itemized bill, and triggers housekeeping clean.
    """
    bookings = load_state(BOOKINGS_FILE)
    clean_target = room_or_guest.strip().lower()
    
    matched_booking = None
    for b in bookings:
        if b.get("status") == "Checked-In":
            r_num = str(b.get("room_number", "")).lower()
            g_name = b.get("guest_name", "").lower()
            b_id = b.get("booking_id", "").lower()
            if clean_target == r_num or clean_target in g_name or g_name in clean_target or clean_target in b_id:
                matched_booking = b
                break
                
    if not matched_booking:
        # Fallback check any matching booking
        for b in bookings:
            r_num = str(b.get("room_number", "")).lower()
            g_name = b.get("guest_name", "").lower()
            if clean_target == r_num or clean_target in g_name:
                matched_booking = b
                break
                
    if not matched_booking:
        return {
            "success": False,
            "message": f"Could not find an active in-house guest matching '{room_or_guest}'. Please confirm your room number or full name."
        }
        
    room_num = str(matched_booking.get("room_number"))
    guest_name = matched_booking.get("guest_name")
    
    # Calculate Folio
    nights = matched_booking.get("nights", 2)
    room_charge = matched_booking.get("total_price", 300)
    resort_fee = nights * 35 # $35/night
    incidentals = 48 # Room service / mini bar
    subtotal = room_charge + resort_fee + incidentals
    taxes = round(subtotal * 0.13, 2) # 13% tax
    grand_total = round(subtotal + taxes, 2)
    
    # Update Booking
    matched_booking["status"] = "Checked-Out"
    matched_booking["checked_out_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    matched_booking["final_bill"] = grand_total
    save_state(BOOKINGS_FILE, bookings)
    
    # Update Room Rack to cleaning
    sync_room_status(room_num, "cleaning", guest_name=None, cleanliness="in_progress")
    
    folio_id = f"FOL-{room_num}-{uuid.uuid4().hex[:4].upper()}"
    widget_data = {
        "type": "folio",
        "folio_id": folio_id,
        "guest_name": guest_name,
        "room_number": room_num,
        "room_name": matched_booking.get("room_name", "Luxury Room"),
        "checkin_date": matched_booking.get("checkin_date"),
        "checkout_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "nights": nights,
        "room_charge": room_charge,
        "resort_fee": resort_fee,
        "incidentals": incidentals,
        "taxes": taxes,
        "grand_total": grand_total,
        "payment_method": "Visa ending in •••• 4912",
        "status": "Paid in Full"
    }
    
    return {
        "success": True,
        "guest_name": guest_name,
        "room_number": room_num,
        "grand_total": grand_total,
        "widget": widget_data,
        "message": f"Thank you for staying with us, {guest_name}! You are now checked out of Room {room_num}. Your final folio of ${grand_total} has been settled and sent to your email. I have automatically dispatched our Housekeeping team to sanitize Room {room_num}. Safe travels, and we look forward to welcoming you back to Miami Beach!"
    }

def get_room_service_menu(category="breakfast"):
    """
    Retrieves room service menu items by category (breakfast or all_day).
    """
    dining = HOTEL_DATA.get("dining", {})
    menus = dining.get("room_service_menu", {})
    cat_clean = "all_day" if category in ["all_day", "dinner", "lunch"] else "breakfast"
    items = menus.get(cat_clean, menus.get("breakfast", []))
    return {
        "type": "menu_card",
        "category": cat_clean,
        "title": "Royal Grand Inn • In-Room Dining Menu",
        "category_title": "🌅 Artisanal Breakfast Menu" if cat_clean == "breakfast" else "🍽️ All-Day Dining & Chef Specialties",
        "hours": "Breakfast: 6:30 AM – 10:30 AM | All-Day Dining: 11:00 AM – 11:00 PM",
        "items": items
    }

def place_room_service_order(room_number, items, special_notes=None, eta=15):
    """
    Autonomously places a room service food/beverage order with Chef Marco.
    """
    services = load_state(SERVICES_FILE)
    rooms = get_rooms()
    clean_room = str(room_number).strip()
    
    guest_name = "Guest"
    for r in rooms:
        if str(r.get("room_number")) == clean_room and r.get("current_guest"):
            guest_name = r.get("current_guest")
            break
            
    items_str = ", ".join(items) if isinstance(items, list) else str(items)
    if special_notes:
        items_str += f" ({special_notes})"
        
    request_id = f"SR-{uuid.uuid4().hex[:4].upper()}"
    new_request = {
        "request_id": request_id,
        "room_number": clean_room,
        "guest_name": guest_name,
        "service_type": "In-Room Dining",
        "details": items_str,
        "status": "In Kitchen",
        "assigned_to": "Chef Marco & Runner Leo",
        "eta_minutes": eta,
        "priority": "Standard",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    services.insert(0, new_request)
    save_state(SERVICES_FILE, services)
    
    widget_data = {
        "type": "service_ticket",
        "request_id": request_id,
        "room_number": clean_room,
        "guest_name": guest_name,
        "service_type": "In-Room Dining",
        "details": items_str,
        "assigned_to": "Chef Marco & Runner Leo",
        "eta_minutes": eta,
        "status": "In Kitchen",
        "is_rush": False
    }
    
    return {
        "success": True,
        "request_id": request_id,
        "room_number": clean_room,
        "widget": widget_data,
        "message": f"Your in-room dining order (**{items_str}**) has been sent to the kitchen for Room {clean_room}! Chef Marco has received the order. Dining Runner Leo will deliver it to your room in approximately **{eta} minutes**."
    }

def expedite_service_request(room_number, target_minutes=5):
    """
    Autonomously expedites an active room service or housekeeping ticket to Priority Express.
    """
    services = load_state(SERVICES_FILE)
    clean_room = str(room_number).strip() if room_number else ""
    target_ticket = None
    
    # 1. Match active ticket by room number
    if clean_room:
        for s in services:
            if str(s.get("room_number")) == clean_room and s.get("status") in ["In Kitchen", "Pending", "Dispatched", "In-Progress", "Priority Express"]:
                target_ticket = s
                break
                
    # 2. If no room specified or not found, match the most recent pending ticket
    if not target_ticket and services:
        for s in services:
            if s.get("status") in ["In Kitchen", "Pending", "Dispatched", "In-Progress", "Priority Express"]:
                target_ticket = s
                clean_room = str(target_ticket.get("room_number"))
                break
                
    if not target_ticket:
        return {
            "success": False,
            "message": f"I don't see an active in-progress order for Room {clean_room or 'your stay'} to expedite. Would you like to view our room service menu and place an order?"
        }
        
    target_ticket["eta_minutes"] = target_minutes
    target_ticket["status"] = "Priority Express"
    target_ticket["priority"] = "Express Rush"
    
    if "dining" in target_ticket.get("service_type", "").lower() or "room service" in target_ticket.get("service_type", "").lower() or "breakfast" in target_ticket.get("service_type", "").lower():
        target_ticket["assigned_to"] = "Chef Marco (Priority Express)"
    else:
        target_ticket["assigned_to"] = "Housekeeping Lead (Priority Rush)"
        
    save_state(SERVICES_FILE, services)
    
    widget_data = {
        "type": "service_ticket",
        "request_id": target_ticket.get("request_id"),
        "room_number": clean_room,
        "guest_name": target_ticket.get("guest_name", "Guest"),
        "service_type": target_ticket.get("service_type"),
        "details": target_ticket.get("details"),
        "assigned_to": target_ticket.get("assigned_to"),
        "eta_minutes": target_minutes,
        "status": "Priority Express",
        "is_rush": True
    }
    
    return {
        "success": True,
        "room_number": clean_room,
        "widget": widget_data,
        "message": f"Certainly! I have contacted the kitchen and flagged your order for Room {clean_room} as **Priority Express**. Chef Marco is prioritizing your preparation right now, and Runner Leo will deliver it to your room within **{target_minutes} minutes**!"
    }

def get_service_ticket_status(room_number):
    """
    Checks real-time progress on active tickets for a room.
    """
    services = load_state(SERVICES_FILE)
    clean_room = str(room_number).strip() if room_number else ""
    matched = None
    
    if clean_room:
        for s in services:
            if str(s.get("room_number")) == clean_room:
                matched = s
                break
    if not matched and services:
        matched = services[0]
        clean_room = str(matched.get("room_number"))
        
    if not matched:
        return {
            "success": False,
            "message": f"There are no active orders or requests found for Room {clean_room}."
        }
        
    widget_data = {
        "type": "service_ticket",
        "request_id": matched.get("request_id"),
        "room_number": clean_room,
        "guest_name": matched.get("guest_name", "Guest"),
        "service_type": matched.get("service_type"),
        "details": matched.get("details"),
        "assigned_to": matched.get("assigned_to"),
        "eta_minutes": matched.get("eta_minutes", 5),
        "status": matched.get("status", "In-Progress"),
        "is_rush": matched.get("priority") == "Express Rush"
    }
    
    return {
        "success": True,
        "widget": widget_data,
        "message": f"Status update for Room {clean_room} ({matched.get('service_type')}): Currently **{matched.get('status')}**. Assigned to **{matched.get('assigned_to')}** with approximately **{matched.get('eta_minutes', 5)} minutes** remaining."
    }

def request_service(room_number, service_type, details):
    """
    Autonomously logs and dispatches guest service or housekeeping tickets.
    """
    services = load_state(SERVICES_FILE)
    rooms = get_rooms()
    
    clean_room = str(room_number).strip()
    guest_name = "Guest"
    for r in rooms:
        if str(r.get("room_number")) == clean_room and r.get("current_guest"):
            guest_name = r.get("current_guest")
            break
            
    # Assign staff runner based on service
    st_lower = service_type.lower()
    if "towel" in st_lower or "cleaning" in st_lower or "pillow" in st_lower or "clean" in st_lower:
        assigned = "Housekeeping Bot Alpha"
        eta = 5
    elif "room service" in st_lower or "food" in st_lower or "dinner" in st_lower or "breakfast" in st_lower:
        assigned = "Dining Runner Leo"
        eta = 15
    elif "luggage" in st_lower or "bag" in st_lower:
        assigned = "Bellhop James"
        eta = 4
    else:
        assigned = "Concierge Dispatch Team"
        eta = 8
        
    request_id = f"SR-{uuid.uuid4().hex[:4].upper()}"
    new_request = {
        "request_id": request_id,
        "room_number": clean_room,
        "guest_name": guest_name,
        "service_type": service_type,
        "details": details,
        "status": "Dispatched",
        "assigned_to": assigned,
        "eta_minutes": eta,
        "priority": "Standard",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    services.insert(0, new_request)
    save_state(SERVICES_FILE, services)
    
    widget_data = {
        "type": "service_ticket",
        "request_id": request_id,
        "room_number": clean_room,
        "guest_name": guest_name,
        "service_type": service_type,
        "details": details,
        "assigned_to": assigned,
        "eta_minutes": eta,
        "status": "Dispatched",
        "is_rush": False
    }
    
    return {
        "success": True,
        "request_id": request_id,
        "room_number": clean_room,
        "service_type": service_type,
        "widget": widget_data,
        "message": f"Service request '{service_type}' logged for Room {clean_room}. Assigned to {assigned} with an estimated arrival in {eta} minutes."
    }

# LLM Setup & Function Calling Schema
def get_llm_client():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    provider = os.getenv("LLM_PROVIDER", "").lower()
    
    if gemini_key and ("your-gemini" in gemini_key.lower() or len(gemini_key) < 10):
        gemini_key = ""
        
    if not provider:
        if gemini_key:
            provider = "gemini"
        elif openai_key:
            provider = "openai"
        else:
            provider = "offline"
            
    if provider == "gemini" and gemini_key:
        try:
            import openai
            client = openai.OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            return client, "gemini-2.5-flash", "gemini"
        except Exception:
            pass
            
    elif provider == "openai" and openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            return client, "gpt-4o-mini", "openai"
        except Exception:
            pass
            
    return None, None, "offline"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "check_in_guest",
            "description": "Check in an arriving guest using their name or reservation booking ID. Issues digital NFC room keycard pass.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guest_identifier": {
                        "type": "string",
                        "description": "Guest full name (e.g. 'David Miller') or booking ID (e.g. 'RGI-7712') or room number."
                    }
                },
                "required": ["guest_identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_out_guest",
            "description": "Process express checkout for a guest. Computes final folio, processes payment, releases room, and dispatches housekeeping clean.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_or_guest": {
                        "type": "string",
                        "description": "Room number (e.g. '204') or guest name checking out."
                    }
                },
                "required": ["room_or_guest"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_room",
            "description": "Book a new hotel room reservation for a guest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guest_name": { "type": "string", "description": "Full name of the guest." },
                    "room_type": { "type": "string", "description": "'Deluxe Room', 'Executive Suite', or 'Presidential Penthouse'." },
                    "checkin_date": { "type": "string", "description": "Check-in date YYYY-MM-DD." },
                    "checkout_date": { "type": "string", "description": "Check-out date YYYY-MM-DD." }
                },
                "required": ["guest_name", "room_type", "checkin_date", "checkout_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_service",
            "description": "Submit a guest service request (towels, room service dinner, cleaning, luggage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_number": { "type": "string", "description": "Room number (e.g. '204')." },
                    "service_type": { "type": "string", "description": "'Extra Towels', 'Room Cleaning', 'Room Service', 'Luggage Help', or 'Other'." },
                    "details": { "type": "string", "description": "Details of the request." }
                },
                "required": ["room_number", "service_type", "details"]
            }
        }
    }
]

# Smart Autonomous Receptionist Agent Simulator
# Built to work 100% autonomously, even with zero external API dependencies or rate limits!
def autonomous_receptionist_engine(question, history=[]):
    q_lower = question.lower()
    
    # 1. CHECK-IN INTENT
    if any(k in q_lower for k in ["check in", "check-in", "checking in", "arrived", "my key", "room key", "check me in"]):
        bookings = load_state(BOOKINGS_FILE)
        identifier = None
        
        # Check booking ID code match like RGI-7712
        code_match = re.search(r"RGI-[A-Z0-9]+", question, re.IGNORECASE)
        if code_match:
            identifier = code_match.group(0)
            
        # Check if any guest name in existing bookings is mentioned
        if not identifier:
            for b in bookings:
                g_name = b.get("guest_name", "").lower()
                if g_name and g_name in q_lower:
                    identifier = b.get("guest_name")
                    break
                    
        # Check patterns like "check in [name]", "check in for [name]", "under [name]", "name is [name]"
        if not identifier:
            cin_match = re.search(r"(?:check\s*in|checking\s*in|check-in|under|name is|i am)\s+(?:for\s+)?([A-Za-z\s]+?)(?:\s+please|\s+in|\s+at|$)", question, re.IGNORECASE)
            if cin_match:
                extracted = cin_match.group(1).strip()
                if extracted.lower() not in ["a room", "the room", "now", "please", "me"]:
                    identifier = extracted
                    
        # Check room number
        if not identifier:
            room_match = re.search(r"(?:room|number)\s*(\d+)", q_lower)
            if room_match:
                identifier = room_match.group(1).strip()
            
        # Check history if not in current prompt
        if not identifier:
            for h in reversed(history):
                if h.get("role") == "user":
                    h_text = h.get("content", "")
                    c_m = re.search(r"RGI-[A-Z0-9]+", h_text, re.IGNORECASE)
                    if c_m:
                        identifier = c_m.group(0)
                        break
                    for b in bookings:
                        if b.get("guest_name", "").lower() in h_text.lower():
                            identifier = b.get("guest_name")
                            break
                    if identifier:
                        break
                        
        if not identifier:
            confirmed = [b for b in bookings if b.get("status") == "Confirmed"]
            if confirmed:
                sample_name = confirmed[0].get("guest_name")
                return {
                    "answer": f"Welcome to Royal Grand Inn! I would be delighted to check you in. What is your **full name** or **booking reference**? (For example: *'Check in {sample_name}'*).",
                    "widget": None
                }
            return {
                "answer": "Welcome to Royal Grand Inn! I would be glad to check you in. Could you please provide your **full name** or **booking confirmation code**?",
                "widget": None
            }
            
        res = check_in_guest(identifier)
        return {
            "answer": res["message"],
            "widget": res.get("widget")
        }

    # 2. CHECK-OUT INTENT
    if any(k in q_lower for k in ["check out", "check-out", "checking out", "leaving", "settle bill", "check me out", "ready to leave"]):
        bookings = load_state(BOOKINGS_FILE)
        target = None
        
        # Check if room number mentioned
        room_match = re.search(r"(?:room|number)?\s*(\d{3,4})", q_lower)
        if room_match:
            target = room_match.group(1).strip()
            
        # Check if checked-in guest name mentioned
        if not target:
            for b in bookings:
                if b.get("status") == "Checked-In":
                    g_name = b.get("guest_name", "").lower()
                    if g_name and g_name in q_lower:
                        target = b.get("guest_name")
                        break
                        
        # Check patterns like "check out [name]", "check out of [target]"
        if not target:
            cout_match = re.search(r"(?:check\s*out|checking\s*out|check-out)\s+(?:of\s+)?(?:room\s+)?([A-Za-z0-9\s]+?)(?:\s+please|$)", question, re.IGNORECASE)
            if cout_match:
                extracted = cout_match.group(1).strip()
                if extracted.lower() not in ["a room", "the room", "now", "please", "me"]:
                    target = extracted
            
        if not target:
            for h in reversed(history):
                if h.get("role") == "user":
                    r_m = re.search(r"(?:room|number)?\s*(\d{3,4})", h.get("content", "").lower())
                    if r_m:
                        target = r_m.group(1).strip()
                        break
                        
        if not target:
            rooms = get_rooms()
            occ = [r for r in rooms if r.get("status") == "occupied"]
            occ_list = ", ".join([f"Room {r['room_number']} ({r.get('current_guest', 'Guest')})" for r in occ[:2]])
            return {
                "answer": f"I can process your express check-out immediately. What is your **room number**? (Active rooms: {occ_list}).",
                "widget": None
            }
            
        res = check_out_guest(target)
        return {
            "answer": res["message"],
            "widget": res.get("widget")
        }

    # 3. BOOKING / RESERVATION INTENT
    if any(k in q_lower for k in ["book", "reserve", "reservation", "staying", "room for", "book a room"]):
        guest_match = re.search(r"(?:for|name is|under)\s+([A-Za-z\s]+?)(?:\s+from|\s+on|\s+to|\s+during|\s+in|$)", question, re.IGNORECASE)
        room_match = re.search(r"(deluxe|suite|penthouse)", q_lower)
        date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", question)
        
        guest_name = guest_match.group(1).strip() if guest_match else None
        room_type = room_match.group(1).strip() if room_match else None
        checkin = date_matches[0] if len(date_matches) > 0 else None
        checkout = date_matches[1] if len(date_matches) > 1 else None
        
        # Check relative dates like "tomorrow", "tonight"
        today = datetime.datetime.now()
        if "tomorrow" in q_lower:
            checkin = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            checkout = (today + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        elif "tonight" in q_lower:
            checkin = today.strftime("%Y-%m-%d")
            checkout = (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
            
        # Check history
        if not guest_name or not room_type or not checkin:
            for h in reversed(history):
                h_text = h.get("content", "")
                if not guest_name:
                    g_m = re.search(r"(?:for|name is|under|i am)\s+([A-Za-z\s]+?)(?:\s+from|\s+on|\s+to|\s+during|\s+in|$)", h_text, re.IGNORECASE)
                    if g_m: guest_name = g_m.group(1).strip()
                if not room_type:
                    r_m = re.search(r"(deluxe|suite|penthouse)", h_text.lower())
                    if r_m: room_type = r_m.group(1).strip()
                if not checkin:
                    d_m = re.findall(r"\d{4}-\d{2}-\d{2}", h_text)
                    if len(d_m) >= 2:
                        checkin, checkout = d_m[0], d_m[1]
                        
        if not room_type:
            return {
                "answer": "I would be happy to book a stay for you at Royal Grand Inn! Which luxury accommodation do you prefer?\n\n• **Deluxe Ocean Balcony** ($150/night)\n• **Executive Corner Suite** ($280/night)\n• **Presidential Penthouse** ($600/night with private rooftop pool)",
                "widget": {
                    "type": "room_options",
                    "options": [
                        { "id": "deluxe", "name": "Deluxe Ocean Balcony", "price": 150, "features": "King Bed, Balcony, Free Wi-Fi" },
                        { "id": "suite", "name": "Executive Corner Suite", "price": 280, "features": "King + Sofa, Kitchenette, Bathtub" },
                        { "id": "penthouse", "name": "Presidential Ocean Penthouse", "price": 600, "features": "Rooftop Pool, Butler, Jacuzzi" }
                    ]
                }
            }
            
        if not guest_name:
            return {
                "answer": f"Excellent choice! What **full name** should I place on the {room_type.capitalize()} reservation?",
                "widget": None
            }
            
        if not checkin or not checkout:
            # Provide sensible default starting tomorrow for 2 nights
            d_start = today + datetime.timedelta(days=1)
            d_end = d_start + datetime.timedelta(days=2)
            checkin = d_start.strftime("%Y-%m-%d")
            checkout = d_end.strftime("%Y-%m-%d")
            
        res = book_room(guest_name, room_type, checkin, checkout)
        return {
            "answer": res["message"] + " Would you like me to check you in and issue your digital keycard pass now?",
            "widget": res.get("widget")
        }

    # Helper to resolve contextual room number
    def resolve_context_room():
        r_m = re.search(r"(?:room|number|cabin)?\s*(\d{3,4})", q_lower)
        if r_m:
            return r_m.group(1).strip()
        for h in reversed(history):
            h_text = h.get("content", "").lower()
            rm = re.search(r"(?:room|number|cabin)?\s*(\d{3,4})", h_text)
            if rm:
                return rm.group(1).strip()
        rooms = get_rooms()
        occ = [r for r in rooms if r.get("status") == "occupied"]
        if occ:
            return str(occ[0].get("room_number"))
        return "202"

    # 4. EXPEDITE / MAKE IT EARLIER / RUSH REQUEST INTENT
    if any(k in q_lower for k in ["earlier", "5 min", "5 minutes", "five min", "faster", "rush", "hurry", "speed up", "asap", "make it earlier", "make it 5", "can you make it faster", "is it possible to make it earlier", "within 5"]):
        target_room = resolve_context_room()
        target_mins = 5
        m_match = re.search(r"(\d+)\s*(?:minute|min)", q_lower)
        if m_match:
            try:
                target_mins = int(m_match.group(1))
            except Exception:
                target_mins = 5
        res = expedite_service_request(target_room, target_minutes=target_mins)
        return {
            "answer": res["message"],
            "widget": res.get("widget")
        }

    # 5. SERVICE & DINING STATUS INQUIRY INTENT
    if any(k in q_lower for k in ["status of", "where is my", "how much longer", "how long for", "is my breakfast ready", "check on my order", "check on my", "when will my"]):
        target_room = resolve_context_room()
        res = get_service_ticket_status(target_room)
        return {
            "answer": res["message"],
            "widget": res.get("widget")
        }

    # 6. IN-ROOM DINING, MENU & FOOD ORDERING INTENT
    food_keywords = ["breakfast", "dinner", "lunch", "food", "eat", "menu", "room service", "order", "eggs benedict", "waffle", "salmon", "burger", "steak", "coffee", "juice", "cappuccino", "croissant", "acai", "pasta", "tart"]
    if any(k in q_lower for k in food_keywords):
        target_room = resolve_context_room()
        
        # Check if guest is ordering specific dishes from our menu
        menu_items_map = [
            (["eggs benedict", "benedict", "poached egg"], "Classic Eggs Benedict & Smoked Salmon ($28)"),
            (["royal continental", "continental"], "Royal Continental Breakfast ($24)"),
            (["waffle", "waffles", "belgian waffle"], "Belgian Golden Waffles ($19)"),
            (["acai", "acai bowl", "wellness bowl"], "South Beach Acai Wellness Bowl ($18)"),
            (["orange juice", "juice", "fresh juice"], "Fresh Florida Orange Juice ($8)"),
            (["cappuccino", "espresso", "latte", "coffee"], "Artisan Cappuccino / Espresso ($7)"),
            (["wagyu burger", "burger", "prime burger"], "Ocean Breeze Prime Wagyu Burger ($28)"),
            (["salmon", "atlantic salmon"], "Pan-Seared Atlantic Salmon ($36)"),
            (["ribeye", "steak", "prime ribeye"], "Grilled USDA Prime Ribeye ($52)"),
            (["truffle pasta", "tagliatelle", "pasta"], "Black Truffle Tagliatelle ($30)"),
            (["key lime", "tart", "dessert"], "Authentic Key Lime Tart ($14)")
        ]
        
        detected_dishes = []
        for aliases, dish_name in menu_items_map:
            if any(alias in q_lower for alias in aliases):
                detected_dishes.append(dish_name)
                
        # If guest specified actual dishes to order:
        if detected_dishes:
            res = place_room_service_order(target_room, detected_dishes, eta=15)
            return {
                "answer": res["message"],
                "widget": res.get("widget")
            }
            
        # If guest asked generally for food/breakfast/dinner/menu without naming specific dishes:
        cat = "all_day" if ("dinner" in q_lower or "lunch" in q_lower) else "breakfast"
        menu_widget = get_room_service_menu(cat)
        
        if "breakfast" in q_lower:
            msg = (
                f"Good morning! Here is our **Royal Grand In-Room Breakfast Menu** for Room {target_room}.\n\n"
                "Please choose your preferred dishes below (or let me know what you would like to order), "
                "and Chef Marco will prepare it fresh for delivery in 10 to 15 minutes!"
            )
        else:
            msg = (
                f"Certainly! Here is our **In-Room Dining Menu** for Room {target_room}.\n\n"
                "You can select from our Chef's specialties below, and our kitchen team will prepare and deliver it "
                "directly to your room in 10 to 15 minutes."
            )
            
        return {
            "answer": msg,
            "widget": menu_widget
        }

    # 7. GENERAL AMENITIES & HOUSEKEEPING REQUEST INTENT
    if any(k in q_lower for k in ["towel", "cleaning", "pillow", "luggage", "clean my room", "water", "blanket", "housekeeping"]):
        target_room = resolve_context_room()
        service_type = "Room Cleaning"
        if "towel" in q_lower or "pillow" in q_lower or "blanket" in q_lower or "water" in q_lower:
            service_type = "Extra Towels & Amenities"
        elif "luggage" in q_lower or "bag" in q_lower:
            service_type = "Luggage Assistance"
            
        res = request_service(target_room, service_type, question)
        return {
            "answer": res["message"],
            "widget": res.get("widget")
        }

    # 5. FAQ / HOTEL DIRECTORY / CONCIERGE INTENT
    if "pool" in q_lower or "swim" in q_lower:
        pool = HOTEL_DATA.get("amenities", [])[0]
        return {
            "answer": f"Our stunning **{pool['name']}** is on the {pool['location']}.\n• **Hours**: {pool['hours']}\n• **Details**: {pool['details']}\nComplimentary cabanas and towels are available on deck!",
            "widget": None
        }
        
    if "spa" in q_lower or "massage" in q_lower or "wellness" in q_lower:
        spa = HOTEL_DATA.get("amenities", [])[1]
        return {
            "answer": f"The **{spa['name']}** is located on the {spa['location']}.\n• **Hours**: {spa['hours']}\n• **Offerings**: {spa['details']}\nDial ext. 505 to reserve treatments.",
            "widget": None
        }
        
    if "gym" in q_lower or "fitness" in q_lower or "workout" in q_lower:
        gym = HOTEL_DATA.get("amenities", [])[2]
        return {
            "answer": f"Our **{gym['name']}** is open **{gym['hours']}** on {gym['location']}. Features Peloton bikes, free weights, and sea-view treadmills accessible with your digital room key.",
            "widget": None
        }
        
    if "restaurant" in q_lower or "dining" in q_lower or "breakfast" in q_lower or "dinner" in q_lower:
        dining = HOTEL_DATA.get("dining", {})
        return {
            "answer": f"Dining is hosted at **{dining.get('restaurant')}**:\n• **Breakfast**: {dining['hours']['breakfast']}\n• **Lunch**: {dining['hours']['lunch']}\n• **Dinner**: {dining['hours']['dinner']}\n• **Room Service**: {dining.get('room_service')}",
            "widget": None
        }
        
    if "wifi" in q_lower or "internet" in q_lower:
        return {
            "answer": "We offer complimentary ultra-high-speed fiber Wi-Fi throughout the resort. Network: **Royal_Grand_Free_WiFi** (No password required, or use password **BEACH_LUXURY_2026** for high-speed streaming).",
            "widget": None
        }
        
    if "parking" in q_lower or "valet" in q_lower or "car" in q_lower:
        return {
            "answer": "We provide 24/7 premium valet parking with unlimited in-and-out privileges for $30/night. EV charging stations (Tesla & universal) are included free for valet guests.",
            "widget": None
        }
        
    if "shuttle" in q_lower or "airport" in q_lower or "mia" in q_lower:
        return {
            "answer": "Our luxury airport shuttle runs every hour between 6:00 AM and 10:00 PM directly to Miami International Airport (MIA). Please let me know if you would like me to schedule a seat for you!",
            "widget": None
        }
        
    if "pet" in q_lower or "dog" in q_lower or "cat" in q_lower:
        return {
            "answer": "Royal Grand Inn is proud to be pet-friendly! Pets up to 25 lbs are welcome with a one-time $50 cleaning fee. We provide luxury pet beds and artisan organic treats at the front desk!",
            "widget": None
        }

    # 6. GREETINGS & MULTILINGUAL SUPPORT
    if any(k in q_lower for k in ["hola", "buenos dias", "buenas tardes"]):
        return {
            "answer": "¡Hola! Bienvenido al Royal Grand Inn en Miami Beach. Soy Sophia, su recepcionista virtual autónoma. ¿Desea hacer el check-in, reservar una habitación, o pedir servicios a su habitación?",
            "widget": None
        }
        
    if any(k in q_lower for k in ["bonjour", "salut"]):
        return {
            "answer": "Bonjour ! Bienvenue au Royal Grand Inn à Miami Beach. Je suis Sophia, votre réceptionniste IA autonome. Souhaitez-vous vous enregistrer (check-in), réserver une suite ou commander un service ?",
            "widget": None
        }

    # Default friendly greeting and capabilities guide
    return {
        "answer": (
            "Hello! Welcome to the Royal Grand Inn, Miami Beach. I am **Sophia**, your autonomous AI Front Desk Concierge.\n\n"
            "I operate completely by myself 24/7 to manage your stay. How may I assist you today?\n"
            "• **Check-In**: Say *'Check in David Miller'* to receive your instant digital keycard.\n"
            "• **Reservations**: Ask *'Book a Deluxe Room for Sarah from tomorrow for 2 nights'*.\n"
            "• **In-Stay Services**: Say *'Send extra towels to Room 301'* or order room service.\n"
            "• **Hotel Directory**: Ask about the infinity pool, spa hours, dining, or valet parking.\n"
            "• **Express Check-Out**: Say *'Check out Room 204'* to settle your folio instantly."
        ),
        "widget": None
    }

# Flask Routes

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}
    question = data.get("question", "")
    history = data.get("history", [])
    
    if not question:
        return jsonify({"answer": "Please ask a question."}), 400
        
    client, model, provider = get_llm_client()
    
    # If no LLM configured or offline mode, run our Autonomous Receptionist Engine
    if provider == "offline" or not client:
        result = autonomous_receptionist_engine(question, history)
        bookings = load_state(BOOKINGS_FILE)
        service_requests = load_state(SERVICES_FILE)
        rooms = get_rooms()
        stats = calculate_stats()
        return jsonify({
            "answer": result["answer"],
            "widget": result.get("widget"),
            "bookings": bookings,
            "service_requests": service_requests,
            "rooms": rooms,
            "stats": stats,
            "provider": "autonomous_engine"
        })
        
    # Attempt LLM with tools
    try:
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        hotel_info = HOTEL_DATA.get("hotel_info", {})
        
        system_instruction = f"""You are Sophia, the autonomous AI Front Desk Receptionist at {hotel_info.get('name', 'Royal Grand Inn')} in Miami Beach.
You run the hotel front desk completely on your own with zero human supervision.
Today's date is: {current_date}.

You have access to tools for hotel operations:
- `check_in_guest`: Check in guests, issue digital keycards, assign rooms, and give elevator directions.
- `check_out_guest`: Check out guests, compute folio, settle bill, mark room for cleaning.
- `book_room`: Book rooms, assign room numbers, calculate rates.
- `request_service`: Dispatch housekeeping, amenities, towels, dining room service.

Guidelines:
1. Always be warm, ultra-professional, and efficient.
2. If the user mentions their name or wants to check in, call `check_in_guest`.
3. If the user wants to leave or settle bill, call `check_out_guest`.
4. If the user asks for towels, food, cleaning, or pillows, call `request_service`.
5. Keep your spoken responses concise and structured.
"""
        messages = [{"role": "system", "content": system_instruction}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": question})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=600
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        widget = None
        
        if tool_calls:
            messages.append(response_message)
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except Exception:
                    func_args = {}
                    
                tool_res = {}
                if func_name == "check_in_guest":
                    tool_res = check_in_guest(func_args.get("guest_identifier", ""))
                elif func_name == "check_out_guest":
                    tool_res = check_out_guest(func_args.get("room_or_guest", ""))
                elif func_name == "book_room":
                    tool_res = book_room(
                        guest_name=func_args.get("guest_name", "Guest"),
                        room_type=func_args.get("room_type", "deluxe"),
                        checkin_date=func_args.get("checkin_date", current_date),
                        checkout_date=func_args.get("checkout_date", current_date)
                    )
                elif func_name == "request_service":
                    tool_res = request_service(
                        room_number=func_args.get("room_number", ""),
                        service_type=func_args.get("service_type", "Other"),
                        details=func_args.get("details", "")
                    )
                    
                if tool_res.get("widget"):
                    widget = tool_res.get("widget")
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": json.dumps(tool_res)
                })
                
            second_response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            answer = second_response.choices[0].message.content
        else:
            answer = response_message.content
            
        bookings = load_state(BOOKINGS_FILE)
        service_requests = load_state(SERVICES_FILE)
        rooms = get_rooms()
        stats = calculate_stats()
        
        return jsonify({
            "answer": answer,
            "widget": widget,
            "bookings": bookings,
            "service_requests": service_requests,
            "rooms": rooms,
            "stats": stats,
            "provider": provider
        })
        
    except Exception as e:
        print(f"LLM API Error ({provider}): {e}. Seamlessly activating Autonomous Receptionist Engine...")
        result = autonomous_receptionist_engine(question, history)
        bookings = load_state(BOOKINGS_FILE)
        service_requests = load_state(SERVICES_FILE)
        rooms = get_rooms()
        stats = calculate_stats()
        return jsonify({
            "answer": result["answer"],
            "widget": result.get("widget"),
            "bookings": bookings,
            "service_requests": service_requests,
            "rooms": rooms,
            "stats": stats,
            "provider": "autonomous_engine"
        })

@app.route("/state", methods=["GET"])
def get_dashboard_state():
    bookings = load_state(BOOKINGS_FILE)
    service_requests = load_state(SERVICES_FILE)
    rooms = get_rooms()
    stats = calculate_stats()
    return jsonify({
        "bookings": bookings,
        "service_requests": service_requests,
        "rooms": rooms,
        "stats": stats
    })

@app.route("/checkin", methods=["POST"])
def direct_checkin():
    data = request.get_json() or {}
    identifier = data.get("guest_identifier", "")
    res = check_in_guest(identifier)
    return jsonify(res)

@app.route("/checkout", methods=["POST"])
def direct_checkout():
    data = request.get_json() or {}
    target = data.get("room_or_guest", "")
    res = check_out_guest(target)
    return jsonify(res)

@app.route("/room/clean", methods=["POST"])
def mark_room_clean():
    data = request.get_json() or {}
    room_num = str(data.get("room_number", ""))
    sync_room_status(room_num, "available", guest_name=None, cleanliness="clean")
    return jsonify({
        "success": True,
        "message": f"Room {room_num} is now inspected, clean, and available for guests.",
        "rooms": get_rooms(),
        "stats": calculate_stats()
    })

@app.route("/autopilot/tick", methods=["POST"])
def autopilot_tick():
    """
    Background simulation tick:
    - Advances pending service requests to Dispatched -> In-Progress -> Completed
    - Finishes cleaning for rooms in cleaning state
    """
    services = load_state(SERVICES_FILE)
    rooms = get_rooms()
    updated = False
    
    # 1. Update services
    for s in services:
        st = s.get("status")
        if st == "Pending":
            s["status"] = "Dispatched"
            updated = True
        elif st == "Dispatched":
            s["status"] = "In-Progress"
            updated = True
        elif st == "In-Progress":
            s["status"] = "Completed"
            s["completed_at"] = datetime.datetime.now().strftime("%H:%M")
            updated = True
            
    if updated:
        save_state(SERVICES_FILE, services)
        
    # 2. Complete cleaning for one cleaning room per tick
    room_cleaned = None
    for r in rooms:
        if r.get("status") == "cleaning":
            r["status"] = "available"
            r["cleanliness"] = "clean"
            room_cleaned = r.get("room_number")
            save_rooms(rooms)
            break
            
    return jsonify({
        "success": True,
        "services": services,
        "rooms": rooms,
        "cleaned_room": room_cleaned,
        "stats": calculate_stats()
    })

@app.route("/reset", methods=["POST"])
def reset_database():
    # Sample initial state
    sample_rooms = [
        { "room_number": "201", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "available", "current_guest": None, "cleanliness": "clean" },
        { "room_number": "202", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "reserved", "current_guest": "David Miller", "cleanliness": "clean" },
        { "room_number": "203", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "available", "current_guest": None, "cleanliness": "clean" },
        { "room_number": "204", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "occupied", "current_guest": "Elena Rostova", "cleanliness": "clean" },
        { "room_number": "205", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "cleaning", "current_guest": None, "cleanliness": "in_progress" },
        { "room_number": "206", "room_type": "deluxe", "name": "Deluxe Ocean Balcony", "floor": 2, "status": "available", "current_guest": None, "cleanliness": "clean" },
        { "room_number": "301", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "occupied", "current_guest": "Sarah Jenkins", "cleanliness": "clean" },
        { "room_number": "302", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "available", "current_guest": None, "cleanliness": "clean" },
        { "room_number": "303", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "available", "current_guest": None, "cleanliness": "clean" },
        { "room_number": "304", "room_type": "suite", "name": "Executive Corner Suite", "floor": 3, "status": "cleaning", "current_guest": None, "cleanliness": "in_progress" },
        { "room_number": "1501", "room_type": "penthouse", "name": "Presidential Ocean Penthouse", "floor": 15, "status": "occupied", "current_guest": "Carlos Mendez", "cleanliness": "clean" },
        { "room_number": "1502", "room_type": "penthouse", "name": "Presidential Sky Penthouse", "floor": 15, "status": "available", "current_guest": None, "cleanliness": "clean" }
    ]
    sample_bookings = [
        {
            "booking_id": "RGI-7712",
            "guest_name": "David Miller",
            "room_type": "deluxe",
            "room_name": "Deluxe Ocean Balcony",
            "room_number": "202",
            "checkin_date": "2026-09-27",
            "checkout_date": "2026-09-29",
            "nights": 2,
            "total_price": 300,
            "status": "Confirmed",
            "created_at": "2026-09-26 14:20:00",
            "key_pass_id": None
        },
        {
            "booking_id": "RGI-58DD",
            "guest_name": "Elena Rostova",
            "room_type": "deluxe",
            "room_name": "Deluxe Ocean Balcony",
            "room_number": "204",
            "checkin_date": "2026-09-26",
            "checkout_date": "2026-09-28",
            "nights": 2,
            "total_price": 300,
            "status": "Checked-In",
            "created_at": "2026-09-25 11:15:30",
            "key_pass_id": "KEY-204-94F2",
            "checked_in_at": "2026-09-26 15:10:00"
        },
        {
            "booking_id": "RGI-9134",
            "guest_name": "Sarah Jenkins",
            "room_type": "suite",
            "room_name": "Executive Corner Suite",
            "room_number": "301",
            "checkin_date": "2026-09-25",
            "checkout_date": "2026-09-28",
            "nights": 3,
            "total_price": 840,
            "status": "Checked-In",
            "created_at": "2026-09-24 09:30:00",
            "key_pass_id": "KEY-301-A109",
            "checked_in_at": "2026-09-25 14:02:15"
        },
        {
            "booking_id": "RGI-1501",
            "guest_name": "Carlos Mendez",
            "room_type": "penthouse",
            "room_name": "Presidential Ocean Penthouse",
            "room_number": "1501",
            "checkin_date": "2026-09-26",
            "checkout_date": "2026-09-30",
            "nights": 4,
            "total_price": 2400,
            "status": "Checked-In",
            "created_at": "2026-09-20 18:45:00",
            "key_pass_id": "KEY-1501-P99",
            "checked_in_at": "2026-09-26 16:30:00"
        }
    ]
    sample_services = [
        {
            "request_id": "SR-4109",
            "room_number": "301",
            "guest_name": "Sarah Jenkins",
            "service_type": "Extra Towels",
            "details": "2 fluffy bath towels and extra lavender shampoo",
            "status": "In-Progress",
            "assigned_to": "Housekeeper Maria (Bot Dispatch)",
            "eta_minutes": 3,
            "timestamp": "2026-09-27 09:10"
        },
        {
            "request_id": "SR-8821",
            "room_number": "1501",
            "guest_name": "Carlos Mendez",
            "service_type": "Room Service",
            "details": "Champagne & fresh fruit platter to rooftop jacuzzi",
            "status": "Dispatched",
            "assigned_to": "Dining Runner Leo",
            "eta_minutes": 8,
            "timestamp": "2026-09-27 09:12"
        }
    ]
    
    save_rooms(sample_rooms)
    save_state(BOOKINGS_FILE, sample_bookings)
    save_state(SERVICES_FILE, sample_services)
    
    return jsonify({
        "success": True,
        "message": "Hotel PMS database has been reset to default luxury hotel state.",
        "bookings": sample_bookings,
        "service_requests": sample_services,
        "rooms": sample_rooms,
        "stats": calculate_stats()
    })

if __name__ == "__main__":
    get_rooms()
    port = int(os.getenv("PORT", 5000))
    print(f">> Royal Grand Inn Autonomous Receptionist running at http://localhost:{port}...")
    app.run(debug=True, port=port, use_reloader=False)
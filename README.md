# Royal Grand Inn • Autonomous AI Hotel Receptionist

An end-to-end, fully autonomous AI Front Desk Receptionist and Hotel Property Management System (PMS) designed to operate 100% unattended 24/7. Powered by **Sophia**, a digital front-desk agent capable of handling guest check-ins, walk-in reservations, in-stay housekeeping & dining requests, express check-out with itemized folio billing, and real-time room rack management.

---

## 🌟 Key Features

### 1. 100% Autonomous Operation
- **Zero Human Staff Required**: Operates autonomously for inquiries, bookings, check-in, service routing, and billing.
- **Continuous Hands-Free Voice Kiosk Mode**: Web Speech Recognition with silence detection, auto-speech turnaround, and customizable voice synthesis.
- **Autonomous Autopilot Demonstration**: One-click simulation showing sequential simulated guest arrival, check-in, service dispatch, and checkout.
- **Self-Healing Fallback Neural Engine**: Seamlessly falls back to an internal natural language rule & semantic engine if external LLM quotas or keys expire.

### 2. Autonomous Front Desk Concierge (Sophia)
- **Digital NFC Keycard Pass**: Emits an Apple Wallet-style luxury keycard with guest name, room number, floor, Wi-Fi credentials, scannable QR code, and interactive door-unlock simulation.
- **Itemized Folio Billing & Settlement**: Computes room rates, resort fees, incidentals, and state/tourist tax, settling charges with official receipt generation.
- **Service Request & Dispatch Queue**: Logs and tracks housekeeping, dining, and luggage requests with animated progress bars and live ETA countdowns.
- **Multi-Language Fluency**: Automatically understands and replies in English, Spanish, French, German, and more.

### 3. Integrated Live Hotel PMS (Property Management System)
- **Real-Time Room Rack Grid**: Tracks Floor 2 (Deluxe Rooms), Floor 3 (Executive Suites), and Floor 15 (Presidential Penthouses) across four distinct states:
  - 🟢 **Available & Clean**
  - 🔵 **Occupied (In-House Guest)**
  - 🟡 **Cleaning (Housekeeping Turnover in Progress)**
  - 🟡 **Reserved (Awaiting Arrival)**
- **Autonomous Background Simulator**: Background PMS tick automatically completes room turnovers and advances service ticket states.
- **Live Hotel KPIs**: Real-time Occupancy Percentage gauge, In-House Guest count, Pending Tickets, and Total Revenue.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Safari, or Firefox)

### Setup & Installation

1. **Activate Python Virtual Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables** (Optional):
   Copy `.env.example` to `.env`:
   ```bash
   LLM_PROVIDER=openai # or gemini or offline
   OPENAI_API_KEY=your_key_here
   GEMINI_API_KEY=your_key_here
   PORT=5000
   ```
   *(Note: The system includes a built-in Autonomous Receptionist Engine that operates completely offline without any API keys).*

4. **Launch the Autonomous Receptionist Server**:
   ```bash
   python app.py
   ```

5. **Access the Web Kiosk**:
   Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the interactive receptionist kiosk web application. |
| `POST` | `/ask` | Primary conversational endpoint with tool routing and rich widget payloads. |
| `GET` | `/state` | Returns the real-time PMS state (rooms, bookings, tickets, and KPIs). |
| `POST` | `/checkin` | Directly executes guest check-in by name or booking reference. |
| `POST` | `/checkout` | Executes express check-out, produces folio, and sets room to cleaning. |
| `POST` | `/room/clean` | Marks a room sanitized, clean, and ready for occupancy. |
| `POST` | `/autopilot/tick` | Background automation tick advancing tickets and room cleaning. |
| `POST` | `/reset` | Restores PMS database to the default sample luxury hotel state. |

---

## 🏗️ Architecture

```
ai-hotel-receptionist/
├── app.py                   # Autonomous Flask PMS & AI Receptionist Server
├── index.html               # Luxury Kiosk Front Desk & Real-Time PMS Interface
├── receptionist_faq.json    # Hotel Directory Knowledge Base
├── rooms.json               # Live Room Rack Inventory State
├── bookings.json            # Hotel Reservations State
├── service_requests.json    # Guest Service Dispatch Queue
├── static/
│   ├── sophia_avatar.jpg    # Generated 8K Receptionist Avatar Portrait
│   └── hotel_lobby.jpg      # Generated 8K Luxury Lobby Background
└── requirements.txt         # Dependencies
```

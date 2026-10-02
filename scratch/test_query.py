import urllib.request
import json

data = {
    "question": "book a deluxe room for tomorrow for John Doe",
    "history": []
}

req = urllib.request.Request(
    "http://127.0.0.1:5000/ask",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        print("Response received:")
        print(res_data["answer"])
        print("\nUpdated Bookings State:")
        print(res_data["bookings"])
except Exception as e:
    print("Error querying server:", e)

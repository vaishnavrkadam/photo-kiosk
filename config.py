import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Printer Configuration
DEFAULT_PRINTER_NAME = "EPSON PM-520 Series"
SIMULATE_PRINTING = False  # Set True to skip sending to hardware during dry-runs

# Storage Directories
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "raw")
PROCESSED_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "processed")
DATABASE_PATH = os.path.join(BASE_DIR, "kiosk.db")

# Razorpay Test Credentials
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_TbT2QN2XcfsEm9")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "7v85wOjsxeXoUCu36KnjFE1H")
CURRENCY = "INR"

# Pricing Configuration (in INR)
PRICING = {
    "4x6": {
        "label": "4 x 6 inches (Standard)",
        "price_per_photo": 50.0,
        "aspect_ratio": 1.5,  # 3:2 ratio
        "width_mm": 101.6,
        "height_mm": 152.4
    },
    "5x7": {
        "label": "5 x 7 inches (Large)",
        "price_per_photo": 80.0,
        "aspect_ratio": 1.4,  # 5:7 ratio
        "width_mm": 127.0,
        "height_mm": 177.8
    },
    "passport": {
        "label": "Passport Photos (8 Copies on 4x6)",
        "price_per_photo": float(os.environ.get("PASSPORT_PRICE", 60.0)),
        "aspect_ratio": 45.0 / 35.0,  # 7:9 ratio (height / width)
        "width_mm": 101.6,
        "height_mm": 152.4
    }
}

# Passport Photo Configuration
PASSPORT_SPEC = {
    "label": "Passport Size Photos (8 Copies Grid)",
    "price_per_sheet": float(os.environ.get("PASSPORT_PRICE", 60.0)),
    "copies_per_sheet": 8,
    "grid_cols": 4,
    "grid_rows": 2,
    "photo_width_mm": 35.0,
    "photo_height_mm": 45.0,
    "paper_size": "4x6"
}

# Laptop Print Agent Authentication
AGENT_SECRET_KEY = os.environ.get("AGENT_SECRET_KEY", "kiosk-print-secret-2026")

# Volume Discount (Percentage off for >= N total prints)
BULK_DISCOUNT_THRESHOLD = 5
BULK_DISCOUNT_PERCENT = 10.0

# Server configuration
# On Render / cloud hosts, PORT is assigned dynamically via environment variable.
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))
SECRET_KEY = os.environ.get("SECRET_KEY", "kiosk-session-secret-katoms-2026")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Katoms@123")

# Cloud Deployment Flag
IS_CLOUD_DEPLOYMENT = os.environ.get("RENDER") is not None or os.environ.get("IS_CLOUD", "false").lower() == "true"


import sqlite3
import os
import json
from datetime import datetime
import config

def get_db():
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.PROCESSED_FOLDER, exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Orders Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                customer_name TEXT,
                customer_phone TEXT,
                total_amount REAL NOT NULL,
                discount_amount REAL DEFAULT 0.0,
                total_items INTEGER NOT NULL,
                total_prints INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, PAID, PRINTING, COMPLETED, FAILED
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                razorpay_signature TEXT,
                payment_method TEXT DEFAULT 'razorpay',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Order Items (Photos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                raw_filename TEXT NOT NULL,
                processed_filename TEXT,
                paper_size TEXT NOT NULL DEFAULT '4x6',
                layout_mode TEXT NOT NULL DEFAULT 'borderless', -- borderless, bordered, polaroid
                color_mode TEXT NOT NULL DEFAULT 'color',       -- color, bw, sepia
                copies INTEGER NOT NULL DEFAULT 1,
                caption TEXT,
                crop_data TEXT, -- JSON string of x, y, width, height, rotate
                price_each REAL NOT NULL,
                subtotal REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',        -- PENDING, READY, PRINTED, FAILED
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        
        # Print Queue
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS print_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                copy_number INTEGER NOT NULL DEFAULT 1,
                total_copies INTEGER NOT NULL DEFAULT 1,
                printer_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED, PRINTING, COMPLETED, FAILED
                attempts INTEGER DEFAULT 0,
                error_message TEXT,
                queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (item_id) REFERENCES order_items (id)
            )
        ''')
        
        # Stats / Settings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Paper Sheet Inventory Table (4x6 and 5x7)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                paper_size TEXT PRIMARY KEY, -- '4x6', '5x7'
                sheets_available INTEGER NOT NULL DEFAULT 50,
                sheets_printed INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize default stock if missing
        cursor.execute('''
            INSERT OR IGNORE INTO inventory (paper_size, sheets_available, sheets_printed)
            VALUES ('4x6', 50, 0)
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO inventory (paper_size, sheets_available, sheets_printed)
            VALUES ('5x7', 20, 0)
        ''')
        
        conn.commit()

def get_inventory():
    """Returns current sheet inventory for all paper sizes."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM inventory").fetchall()
        inv = {}
        for r in rows:
            inv[r["paper_size"]] = {
                "available": r["sheets_available"],
                "printed": r["sheets_printed"],
                "updated_at": r["updated_at"]
            }
        return inv

def update_inventory(paper_size, sheets_available, conn=None):
    """Sets the available sheet count for a paper size."""
    if conn is not None:
        conn.execute('''
            INSERT INTO inventory (paper_size, sheets_available, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(paper_size) DO UPDATE SET
                sheets_available = excluded.sheets_available,
                updated_at = CURRENT_TIMESTAMP
        ''', (paper_size, max(0, int(sheets_available))))
    else:
        with get_db() as c:
            c.execute('''
                INSERT INTO inventory (paper_size, sheets_available, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(paper_size) DO UPDATE SET
                    sheets_available = excluded.sheets_available,
                    updated_at = CURRENT_TIMESTAMP
            ''', (paper_size, max(0, int(sheets_available))))
            c.commit()

def deduct_inventory(paper_size, count=1, conn=None):
    """Deducts sheets_available and increments sheets_printed."""
    if conn is not None:
        conn.execute('''
            UPDATE inventory
            SET sheets_available = MAX(0, sheets_available - ?),
                sheets_printed = sheets_printed + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE paper_size = ?
        ''', (count, count, paper_size))
    else:
        with get_db() as c:
            c.execute('''
                UPDATE inventory
                SET sheets_available = MAX(0, sheets_available - ?),
                    sheets_printed = sheets_printed + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE paper_size = ?
            ''', (count, count, paper_size))
            c.commit()

def check_inventory_sufficient(items):
    """
    Checks if there are sufficient sheets available for the given order items.
    Returns (True, None) or (False, user_friendly_error_message).
    """
    needed = {"4x6": 0, "5x7": 0}
    for item in items:
        size = item.get("paper_size", "4x6")
        copies = max(1, int(item.get("copies", 1)))
        # Passport photos are printed on 4x6 paper sheets
        stock_key = "4x6" if size in ("4x6", "passport") else "5x7"
        needed[stock_key] = needed.get(stock_key, 0) + copies

    current_inv = get_inventory()
    for stock_key, count_needed in needed.items():
        if count_needed > 0:
            avail = current_inv.get(stock_key, {}).get("available", 0)
            if count_needed > avail:
                size_label = "4x6 inch" if stock_key == "4x6" else "5x7 inch"
                if avail <= 0:
                    return False, f"Sorry, {size_label} photo paper is currently out of stock. Please ask the kiosk operator to reload paper."
                else:
                    return False, f"Insufficient paper: you requested {count_needed} sheets, but only {avail} sheets of {size_label} paper are currently available in the printer."

    return True, None

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")


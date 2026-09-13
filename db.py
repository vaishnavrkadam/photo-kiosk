import sqlite3
import os
import json
from datetime import datetime
import config

def get_db():
    conn = sqlite3.connect(config.DATABASE_PATH)
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
        
        conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")

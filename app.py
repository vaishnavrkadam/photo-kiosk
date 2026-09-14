import os
import uuid
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, send_file
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

import config
from db import init_db, get_db, get_inventory, update_inventory, deduct_inventory, check_inventory_sufficient
from image_processor import process_photo, generate_passport_grid
from printer_service import printer_service
from payment_service import payment_service

# Initialize Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("App")

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = config.PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'heic', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------- Customer UI Pages -----------------

@app.route('/')
def index():
    return render_template('index.html', pricing=config.PRICING, rzp_key=config.RAZORPAY_KEY_ID)

@app.route('/order/<order_id>')
def order_view(order_id):
    with get_db() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return "Order not found", 404
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    return render_template('order_status.html', order=order, items=items)

@app.route('/qr')
@app.route('/kiosk_qr_code.png')
def serve_qr():
    return send_from_directory(config.BASE_DIR, 'kiosk_qr_code.png')

# ----------------- Admin UI Pages -----------------

@app.route('/admin')
def admin():
    return render_template('admin.html', pricing=config.PRICING, default_printer=printer_service.get_active_printer())

# ----------------- Customer API Endpoints -----------------

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'photos' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = request.files.getlist('photos')
    results = []

    for file in files:
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            raw_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(raw_path)

            # Read dimensions & orientation
            try:
                with Image.open(raw_path) as img:
                    width, height = img.size
            except Exception:
                width, height = (1200, 1800)

            results.append({
                'original_name': file.filename,
                'raw_filename': unique_name,
                'url': f"/static/uploads/raw/{unique_name}",
                'width': width,
                'height': height
            })

    return jsonify({'success': True, 'files': results})

@app.route('/api/passport/preview', methods=['POST'])
def passport_preview():
    """Generates a temporary preview of the 8-photo passport grid."""
    data = request.get_json() or {}
    raw_filename = data.get('raw_filename')
    crop_box = data.get('crop_box')
    color_mode = data.get('color_mode', 'color')

    if not raw_filename:
        return jsonify({'error': 'Missing raw_filename'}), 400

    raw_path = os.path.join(app.config['UPLOAD_FOLDER'], raw_filename)
    if not os.path.exists(raw_path):
        return jsonify({'error': 'Image file not found'}), 404

    preview_id = f"prev_{uuid.uuid4().hex[:8]}.jpg"
    preview_path = os.path.join(app.config['PROCESSED_FOLDER'], preview_id)

    try:
        generate_passport_grid(
            raw_path=raw_path,
            output_path=preview_path,
            crop_box=crop_box,
            color_mode=color_mode
        )
        return jsonify({
            'success': True,
            'preview_url': f"/static/uploads/processed/{preview_id}"
        })
    except Exception as e:
        logger.error(f"Error generating passport preview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/photo/preview', methods=['POST'])
def photo_preview():
    """Generates a temporary print-ready preview of standard photo with user crop & layout."""
    data = request.get_json() or {}
    raw_filename = data.get('raw_filename')
    paper_size = data.get('paper_size', '4x6')
    layout_mode = data.get('layout_mode', 'borderless')
    color_mode = data.get('color_mode', 'color')
    crop_box = data.get('crop_box')
    caption = data.get('caption', '')

    if not raw_filename:
        return jsonify({'error': 'Missing raw_filename'}), 400

    raw_path = os.path.join(app.config['UPLOAD_FOLDER'], raw_filename)
    if not os.path.exists(raw_path):
        return jsonify({'error': 'Image file not found'}), 404

    preview_id = f"prev_std_{uuid.uuid4().hex[:8]}.jpg"
    preview_path = os.path.join(app.config['PROCESSED_FOLDER'], preview_id)

    try:
        process_photo(
            raw_path=raw_path,
            output_path=preview_path,
            paper_size=paper_size,
            layout_mode=layout_mode,
            color_mode=color_mode,
            crop_box=crop_box,
            caption=caption
        )
        return jsonify({
            'success': True,
            'preview_url': f"/static/uploads/processed/{preview_id}"
        })
    except Exception as e:
        logger.error(f"Error generating photo preview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory', methods=['GET'])
def public_get_inventory():
    """Returns current available paper sheet counts."""
    return jsonify({
        'success': True,
        'inventory': get_inventory()
    })

@app.route('/api/admin/inventory', methods=['POST'])
def admin_set_inventory():
    """Allows admin to update paper stock (sheets_available)."""
    data = request.get_json() or {}
    if 'paper_size' in data and 'sheets_available' in data:
        update_inventory(data['paper_size'], data['sheets_available'])
    else:
        for size in ('4x6', '5x7'):
            if size in data:
                update_inventory(size, data[size])

    return jsonify({
        'success': True,
        'inventory': get_inventory(),
        'message': 'Inventory updated successfully'
    })

@app.route('/api/order/calculate', methods=['POST'])
def calculate_price():
    data = request.get_json() or {}
    items = data.get('items', [])

    subtotal = 0.0
    total_prints = 0

    for item in items:
        size = item.get('paper_size', '4x6')
        copies = max(1, int(item.get('copies', 1)))
        price_each = config.PRICING.get(size, config.PRICING["4x6"])["price_per_photo"]
        subtotal += price_each * copies
        total_prints += copies

    discount = 0.0
    if total_prints >= config.BULK_DISCOUNT_THRESHOLD:
        discount = round(subtotal * (config.BULK_DISCOUNT_PERCENT / 100.0), 2)

    total_amount = max(0.0, round(subtotal - discount, 2))

    return jsonify({
        'subtotal': subtotal,
        'discount': discount,
        'total_prints': total_prints,
        'total_amount': total_amount,
        'currency': config.CURRENCY
    })

@app.route('/api/order/create', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    items = data.get('items', [])
    customer_name = data.get('customer_name', 'Customer')
    customer_phone = data.get('customer_phone', '')

    if not items:
        return jsonify({'error': 'No photos provided'}), 400

    # 1. Enforce Paper Sheet Inventory Limits
    sufficient, inv_error = check_inventory_sufficient(items)
    if not sufficient:
        return jsonify({'error': inv_error, 'out_of_stock': True}), 400

    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # Calculate Totals
    subtotal = 0.0
    total_prints = 0
    item_records = []

    for item in items:
        size = item.get('paper_size', '4x6')
        layout = item.get('layout_mode', 'borderless')
        color = item.get('color_mode', 'color')
        copies = max(1, int(item.get('copies', 1)))
        caption = item.get('caption', '')
        crop_box = item.get('crop_box') # [x, y, w, h]
        raw_filename = item.get('raw_filename')
        original_name = item.get('original_name', raw_filename)

        price_each = config.PRICING.get(size, config.PRICING["4x6"])["price_per_photo"]
        item_subtotal = price_each * copies
        subtotal += item_subtotal
        total_prints += copies

        # Pre-render 300 DPI print-ready image
        raw_path = os.path.join(app.config['UPLOAD_FOLDER'], raw_filename)
        processed_filename = f"{order_id}_{len(item_records) + 1}.jpg"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)

        process_photo(
            raw_path=raw_path,
            output_path=processed_path,
            paper_size=size,
            layout_mode=layout,
            color_mode=color,
            crop_box=crop_box,
            caption=caption
        )

        item_records.append({
            'original_filename': original_name,
            'raw_filename': raw_filename,
            'processed_filename': processed_path,
            'paper_size': size,
            'layout_mode': layout,
            'color_mode': color,
            'copies': copies,
            'caption': caption,
            'crop_data': json.dumps(crop_box) if crop_box else None,
            'price_each': price_each,
            'subtotal': item_subtotal
        })

    # Discount
    discount = 0.0
    if total_prints >= config.BULK_DISCOUNT_THRESHOLD:
        discount = round(subtotal * (config.BULK_DISCOUNT_PERCENT / 100.0), 2)
    total_amount = max(1.0, round(subtotal - discount, 2))  # Razorpay minimum is 1 INR

    # Save to Database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (id, customer_name, customer_phone, total_amount, discount_amount, 
                                total_items, total_prints, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        ''', (order_id, customer_name, customer_phone, total_amount, discount, len(item_records), total_prints))

        for rec in item_records:
            cursor.execute('''
                INSERT INTO order_items (order_id, original_filename, raw_filename, processed_filename, 
                                        paper_size, layout_mode, color_mode, copies, caption, crop_data, 
                                        price_each, subtotal, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            ''', (order_id, rec['original_filename'], rec['raw_filename'], rec['processed_filename'],
                  rec['paper_size'], rec['layout_mode'], rec['color_mode'], rec['copies'], rec['caption'],
                  rec['crop_data'], rec['price_each'], rec['subtotal']))
        conn.commit()

    # Create Gateway Order
    try:
        rzp_order = payment_service.create_order(order_id, total_amount)
        with get_db() as conn:
            conn.execute("UPDATE orders SET razorpay_order_id = ? WHERE id = ?", (rzp_order['id'], order_id))
            conn.commit()

        return jsonify({
            'success': True,
            'order_id': order_id,
            'razorpay_order_id': rzp_order['id'],
            'razorpay_key_id': config.RAZORPAY_KEY_ID,
            'amount_paise': rzp_order['amount'],
            'amount_inr': total_amount,
            'currency': config.CURRENCY,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'is_simulation': rzp_order.get('is_simulation', False)
        })
    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        return jsonify({'error': f'Failed to create payment order: {str(e)}'}), 500

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    if not order_id:
        return jsonify({'error': 'Missing order_id'}), 400

    # Verify signature
    valid = payment_service.verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature)
    if not valid:
        with get_db() as conn:
            conn.execute('''
                UPDATE orders 
                SET status = 'FAILED', error_message = 'Payment signature verification failed'
                WHERE id = ?
            ''', (order_id,))
            conn.commit()
        return jsonify({'error': 'Payment signature verification failed'}), 400

    # Update database to PENDING (payment confirmed, awaiting physical print)
    with get_db() as conn:
        conn.execute('''
            UPDATE orders 
            SET status = 'PENDING', razorpay_payment_id = ?, razorpay_signature = ?, paid_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (razorpay_payment_id, razorpay_signature, order_id))

        # Deduct paper stock from inventory
        order_items = conn.execute("SELECT paper_size, copies FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        for it in order_items:
            stock_key = '4x6' if it['paper_size'] in ('4x6', 'passport') else '5x7'
            deduct_inventory(stock_key, it['copies'], conn=conn)

        conn.commit()

    # Enqueue to Print Spooler!
    printer_service.enqueue_order(order_id)

    return jsonify({
        'success': True,
        'order_id': order_id,
        'redirect_url': f"/order/{order_id}"
    })

@app.route('/api/order/<order_id>/status', methods=['GET'])
def get_order_status(order_id):
    with get_db() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        jobs = conn.execute("SELECT * FROM print_queue WHERE order_id = ? ORDER BY id ASC", (order_id,)).fetchall()

    completed_jobs = sum(1 for j in jobs if j['status'] == 'COMPLETED')
    total_jobs = len(jobs)
    current_printing = next((j for j in jobs if j['status'] == 'PRINTING'), None)

    return jsonify({
        'order_id': order['id'],
        'status': order['status'],
        'error_message': order['error_message'],
        'total_prints': order['total_prints'],
        'total_amount': order['total_amount'],
        'completed_jobs': completed_jobs,
        'total_jobs': total_jobs,
        'current_copy': f"{current_printing['copy_number']}/{current_printing['total_copies']}" if current_printing else None,
        'items': [dict(it) for it in items],
        'jobs': [dict(j) for j in jobs]
    })

# ----------------- Remote Laptop Print Agent Endpoints -----------------

AGENT_STATE = {
    "last_seen": None,
    "printer_name": None,
    "status": "OFFLINE",
    "installed_printers": []
}

def verify_agent_auth():
    auth_header = request.headers.get("X-Agent-Secret")
    query_auth = request.args.get("secret")
    return (auth_header == config.AGENT_SECRET_KEY) or (query_auth == config.AGENT_SECRET_KEY)

@app.route('/api/agent/jobs', methods=['GET'])
def agent_get_jobs():
    if not verify_agent_auth():
        return jsonify({'error': 'Unauthorized: invalid agent secret'}), 401

    with get_db() as conn:
        jobs = conn.execute('''
            SELECT q.id, q.order_id, q.item_id, q.copy_number, q.total_copies, q.status,
                   i.paper_size, i.layout_mode, i.color_mode, o.customer_name
            FROM print_queue q
            JOIN order_items i ON q.item_id = i.id
            JOIN orders o ON q.order_id = o.id
            WHERE q.status = 'QUEUED'
            ORDER BY q.id ASC
            LIMIT 5
        ''').fetchall()

    return jsonify({
        'success': True,
        'jobs': [dict(j) for j in jobs]
    })

@app.route('/api/agent/download/<int:job_id>', methods=['GET'])
def agent_download_job(job_id):
    if not verify_agent_auth():
        return jsonify({'error': 'Unauthorized: invalid agent secret'}), 401

    with get_db() as conn:
        job = conn.execute('''
            SELECT q.id, i.processed_filename
            FROM print_queue q
            JOIN order_items i ON q.item_id = i.id
            WHERE q.id = ?
        ''', (job_id,)).fetchone()

    if not job or not job['processed_filename'] or not os.path.exists(job['processed_filename']):
        return jsonify({'error': 'Job or processed file not found'}), 404

    return send_file(job['processed_filename'], mimetype='image/jpeg')

@app.route('/api/agent/job/<int:job_id>/status', methods=['POST'])
def agent_update_job_status(job_id):
    if not verify_agent_auth():
        return jsonify({'error': 'Unauthorized: invalid agent secret'}), 401

    data = request.get_json() or {}
    new_status = data.get('status')
    error_msg = data.get('error_message', '')

    if new_status not in ('PRINTING', 'COMPLETED', 'FAILED'):
        return jsonify({'error': 'Invalid status'}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        job = cursor.execute("SELECT * FROM print_queue WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        order_id = job['order_id']
        item_id = job['item_id']

        if new_status == 'PRINTING':
            cursor.execute('''
                UPDATE print_queue SET status = 'PRINTING', started_at = CURRENT_TIMESTAMP, attempts = attempts + 1
                WHERE id = ?
            ''', (job_id,))
        elif new_status == 'COMPLETED':
            cursor.execute('''
                UPDATE print_queue SET status = 'COMPLETED', finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (job_id,))
            cursor.execute('''
                UPDATE order_items SET status = 'PRINTED' WHERE id = ?
            ''', (item_id,))

            remaining = cursor.execute('''
                SELECT COUNT(*) as count FROM print_queue
                WHERE order_id = ? AND status != 'COMPLETED'
            ''', (order_id,)).fetchone()["count"]

            if remaining == 0:
                cursor.execute('''
                    UPDATE orders SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (order_id,))
                logger.info(f"Order {order_id} marked COMPLETED via remote agent")
        elif new_status == 'FAILED':
            cursor.execute('''
                UPDATE print_queue SET status = 'FAILED', error_message = ?
                WHERE id = ?
            ''', (error_msg, job_id))
            cursor.execute('''
                UPDATE orders SET status = 'PENDING', error_message = ?
                WHERE id = ?
            ''', (f"Printer error: {error_msg}", order_id))

        conn.commit()

    return jsonify({'success': True, 'job_id': job_id, 'status': new_status})

@app.route('/api/agent/heartbeat', methods=['POST'])
def agent_heartbeat():
    if not verify_agent_auth():
        return jsonify({'error': 'Unauthorized: invalid agent secret'}), 401

    data = request.get_json() or {}
    AGENT_STATE["last_seen"] = datetime.now().isoformat()
    AGENT_STATE["printer_name"] = data.get("printer_name", "Unknown")
    AGENT_STATE["status"] = data.get("status", "ONLINE")
    AGENT_STATE["installed_printers"] = data.get("installed_printers", [])

    return jsonify({'success': True, 'acknowledged_at': AGENT_STATE["last_seen"]})

# ----------------- Admin API Endpoints -----------------

@app.route('/api/admin/status', methods=['GET'])
def get_admin_status():
    with get_db() as conn:
        recent_orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 25").fetchall()
        queue = conn.execute('''
            SELECT q.*, i.original_filename, i.paper_size, o.customer_name
            FROM print_queue q
            JOIN order_items i ON q.item_id = i.id
            JOIN orders o ON q.order_id = o.id
            WHERE q.status IN ('QUEUED', 'PRINTING')
            ORDER BY q.id ASC
        ''').fetchall()
        
        total_printed = conn.execute("SELECT COUNT(*) as count FROM print_queue WHERE status = 'COMPLETED'").fetchone()['count']
        today_printed = conn.execute("SELECT COUNT(*) as count FROM print_queue WHERE status = 'COMPLETED' AND date(finished_at) = date('now')").fetchone()['count']

    # Check if remote print agent is online (heartbeat within 25 seconds)
    is_agent_online = False
    if AGENT_STATE.get("last_seen"):
        try:
            last_dt = datetime.fromisoformat(AGENT_STATE["last_seen"])
            is_agent_online = (datetime.now() - last_dt).total_seconds() < 25
        except Exception:
            pass

    return jsonify({
        'active_printer': AGENT_STATE.get("printer_name") or printer_service.get_active_printer(),
        'installed_printers': AGENT_STATE.get("installed_printers") or printer_service.get_installed_printers(),
        'queue': [dict(q) for q in queue],
        'recent_orders': [dict(o) for o in recent_orders],
        'total_printed': total_printed,
        'today_printed': today_printed,
        'inventory': get_inventory(),
        'agent': {
            'is_online': is_agent_online,
            'last_seen': AGENT_STATE.get("last_seen"),
            'printer_name': AGENT_STATE.get("printer_name"),
            'status': "ONLINE" if is_agent_online else "OFFLINE"
        }
    })

@app.route('/api/admin/reprint', methods=['POST'])
def admin_reprint():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'error': 'Missing order_id'}), 400
    printer_service.enqueue_order(order_id)
    return jsonify({'success': True, 'message': f'Order {order_id} re-enqueued for printing'})

@app.route('/api/admin/test-print', methods=['POST'])
def admin_test_print():
    """Generates a test card and prints it to verify PM-520 hardware connection."""
    test_img_path = os.path.join(app.config['PROCESSED_FOLDER'], "hardware_test_card.jpg")
    
    # Generate test card with color bars and timestamp
    test_card = Image.new("RGB", (1800, 1200), (255, 255, 255))
    draw = ImageDraw.Draw(test_card)
    
    # Color Bars
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255), (50, 50, 50)]
    bar_w = 1800 // len(colors)
    for i, c in enumerate(colors):
        draw.rectangle([i * bar_w, 0, (i + 1) * bar_w, 200], fill=c)

    # Info Text
    try:
        font_large = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 60)
        font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((100, 350), "EPSON PictureMate PM-520 Hardware Test", fill=(20, 20, 20), font=font_large)
    draw.text((100, 480), f"Status: Spooler Ready | Native 756 DPI Profile", fill=(60, 60, 60), font=font_small)
    draw.text((100, 560), f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(60, 60, 60), font=font_small)
    draw.text((100, 640), "Smart Photo Kiosk System Online", fill=(16, 185, 129), font=font_small)

    test_card.save(test_img_path, quality=96)

    success, msg = printer_service.print_image(test_img_path, job_title="Kiosk Hardware Test Page")
    return jsonify({'success': success, 'message': msg})

# Start Print Queue Worker only if local mode (not cloud deployment)
with app.app_context():
    init_db()
    if not getattr(config, 'IS_CLOUD_DEPLOYMENT', False):
        try:
            printer_service.start_worker()
        except Exception as e:
            logger.warning(f"Local printer worker not started: {e}")

if __name__ == '__main__':
    logger.info(f"Starting Photo Kiosk Server on http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)

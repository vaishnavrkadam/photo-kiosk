import time
import threading
import logging
from PIL import Image, ImageWin
import config
from db import get_db

# Try importing win32 printing modules
try:
    import win32print
    import win32ui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

logger = logging.getLogger("PrinterService")
logger.setLevel(logging.INFO)

class PrinterService:
    def __init__(self):
        self.running = False
        self.worker_thread = None
        self.lock = threading.Lock()

    def get_installed_printers(self):
        """Returns list of installed printer names on Windows."""
        if not WIN32_AVAILABLE:
            return ["Simulated Printer (Virtual)"]
        
        printers = []
        try:
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            for p in win32print.EnumPrinters(flags):
                printers.append(p[2])
        except Exception as e:
            logger.error(f"Error enumerating printers: {e}")
            try:
                printers.append(win32print.GetDefaultPrinter())
            except Exception:
                printers.append("EPSON PM-520 Series")
        return printers

    def get_active_printer(self):
        """Gets target printer name, verifying EPSON PM-520 or default."""
        installed = self.get_installed_printers()
        if config.DEFAULT_PRINTER_NAME in installed:
            return config.DEFAULT_PRINTER_NAME
        # Fallback to default printer if PM-520 not found
        if WIN32_AVAILABLE:
            try:
                return win32print.GetDefaultPrinter()
            except Exception:
                pass
        return installed[0] if installed else config.DEFAULT_PRINTER_NAME

    def print_image(self, image_path, job_title="Photo Print", printer_name=None):
        """
        Sends an image file directly to the Windows printer DC silently.
        """
        if config.SIMULATE_PRINTING or not WIN32_AVAILABLE:
            logger.info(f"[SIMULATOR] Simulating print for {image_path}")
            time.sleep(3)
            return True, "Printed successfully (Simulated)"

        target_printer = printer_name or self.get_active_printer()
        logger.info(f"Sending {image_path} to printer: {target_printer}")

        try:
            # 1. Open image
            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # 2. Create Printer Device Context
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(target_printer)

            # Get physical printable dimensions and DPI
            printer_w = hDC.GetDeviceCaps(win32con.HORZRES)
            printer_h = hDC.GetDeviceCaps(win32con.VERTRES)
            dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
            dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)

            # 3. Orient image to match printer orientation
            img_is_landscape = (img.width > img.height)
            printer_is_landscape = (printer_w > printer_h)

            if img_is_landscape != printer_is_landscape:
                img = img.rotate(90, expand=True)

            # 4. Scale image to fill printable area (borderless / fit)
            scale = max(printer_w / img.width, printer_h / img.height)
            render_w = int(img.width * scale)
            render_h = int(img.height * scale)
            img_rendered = img.resize((render_w, render_h), Image.Resampling.LANCZOS)

            offset_x = (printer_w - render_w) // 2
            offset_y = (printer_h - render_h) // 2

            # 5. Start print spooling
            hDC.StartDoc(job_title)
            hDC.StartPage()

            dib = ImageWin.Dib(img_rendered)
            dib.draw(hDC.GetHandleOutput(), (offset_x, offset_y, offset_x + render_w, offset_y + render_h))

            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()
            return True, "Printed successfully"
        except Exception as e:
            logger.error(f"Printing failed: {e}", exc_info=True)
            return False, str(e)

    def enqueue_order(self, order_id):
        """Enqueues all paid items of an order into the print queue."""
        with get_db() as conn:
            cursor = conn.cursor()
            items = cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
            active_printer = self.get_active_printer()

            for item in items:
                copies = item["copies"]
                for copy_num in range(1, copies + 1):
                    cursor.execute('''
                        INSERT INTO print_queue (order_id, item_id, copy_number, total_copies, printer_name, status)
                        VALUES (?, ?, ?, ?, ?, 'QUEUED')
                    ''', (order_id, item["id"], copy_num, copies, active_printer))

            # Update order status to PENDING
            cursor.execute("UPDATE orders SET status = 'PENDING' WHERE id = ?", (order_id,))
            conn.commit()
            logger.info(f"Order {order_id} enqueued ({len(items)} items)")

    def start_worker(self):
        """Starts background queue processor thread."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_queue_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Print Queue Worker started.")

    def _process_queue_loop(self):
        while self.running:
            try:
                self._process_next_job()
            except Exception as e:
                logger.error(f"Error in print worker loop: {e}")
            time.sleep(2)

    def _process_next_job(self):
        with self.lock:
            with get_db() as conn:
                cursor = conn.cursor()
                # Find oldest QUEUED job
                job = cursor.execute('''
                    SELECT q.*, i.processed_filename, i.paper_size, i.order_id, o.customer_name
                    FROM print_queue q
                    JOIN order_items i ON q.item_id = i.id
                    JOIN orders o ON q.order_id = o.id
                    WHERE q.status = 'QUEUED'
                    ORDER BY q.id ASC
                    LIMIT 1
                ''').fetchone()

                if not job:
                    return

                job_id = job["id"]
                order_id = job["order_id"]
                image_path = job["processed_filename"]
                copy_num = job["copy_number"]
                total_copies = job["total_copies"]
                printer_name = job["printer_name"]

                # Mark queue job as PRINTING
                cursor.execute('''
                    UPDATE print_queue SET status = 'PRINTING', started_at = CURRENT_TIMESTAMP, attempts = attempts + 1
                    WHERE id = ?
                ''', (job_id,))
                conn.commit()

            # Execute print outside DB lock
            job_title = f"Photo Order {order_id[:8]} (Copy {copy_num}/{total_copies})"
            success, msg = self.print_image(image_path, job_title=job_title, printer_name=printer_name)

            with get_db() as conn:
                cursor = conn.cursor()
                if success:
                    cursor.execute('''
                        UPDATE print_queue SET status = 'COMPLETED', finished_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (job_id,))
                    cursor.execute('''
                        UPDATE order_items SET status = 'PRINTED' WHERE id = ?
                    ''', (job["item_id"],))
                else:
                    cursor.execute('''
                        UPDATE print_queue SET status = 'FAILED', error_message = ?
                        WHERE id = ?
                    ''', (msg, job_id))
                    cursor.execute('''
                        UPDATE orders SET status = 'PENDING', error_message = ?
                        WHERE id = ?
                    ''', (f"Print issue: {msg}", order_id))

                # Check if all jobs for this order are completed
                remaining = cursor.execute('''
                    SELECT COUNT(*) as count FROM print_queue
                    WHERE order_id = ? AND status != 'COMPLETED'
                ''', (order_id,)).fetchone()["count"]

                if remaining == 0:
                    cursor.execute('''
                        UPDATE orders SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (order_id,))
                    logger.info(f"Order {order_id} fully COMPLETED!")

                conn.commit()

printer_service = PrinterService()

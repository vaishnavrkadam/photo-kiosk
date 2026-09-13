"""
Smart Photo Kiosk - Laptop Print Agent
======================================
Runs on the Windows laptop connected to the Epson PictureMate PM-520 printer.
Polls the cloud-hosted server for pending print jobs, prints them silently via
the Windows print spooler, and updates the cloud database with real-time status.
"""

import os
import sys
import time
import json
import logging
import tempfile
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PrintAgent] %(message)s"
)
logger = logging.getLogger("PrintAgent")

# Configuration (can be overridden via environment variables or agent_config.json)
CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "agent_config.json")

def load_config():
    cfg = {
        "server_url": "http://localhost:5000",
        "agent_secret": "kiosk-print-secret-2026",
        "printer_name": "EPSON PM-520 Series",
        "poll_interval_seconds": 3,
        "heartbeat_interval_seconds": 15
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception as e:
            logger.warning(f"Could not load agent_config.json: {e}")

    # Environment variable overrides
    if "KIOSK_SERVER_URL" in os.environ:
        cfg["server_url"] = os.environ["KIOSK_SERVER_URL"].rstrip("/")
    if "AGENT_SECRET_KEY" in os.environ:
        cfg["agent_secret"] = os.environ["AGENT_SECRET_KEY"]
    if "DEFAULT_PRINTER_NAME" in os.environ:
        cfg["printer_name"] = os.environ["DEFAULT_PRINTER_NAME"]

    return cfg

# Import printer service
try:
    from printer_service import printer_service
    import win32print
    WIN32_READY = True
except ImportError:
    WIN32_READY = False
    logger.warning("win32print not available! Agent will run in SIMULATED mode.")


class PrintAgent:
    def __init__(self):
        self.config = load_config()
        self.server_url = self.config["server_url"].rstrip("/")
        self.secret = self.config["agent_secret"]
        self.poll_interval = self.config["poll_interval_seconds"]
        self.heartbeat_interval = self.config["heartbeat_interval_seconds"]
        self.last_heartbeat = 0

        self.headers = {
            "X-Agent-Secret": self.secret,
            "User-Agent": "KioskLaptopPrintAgent/1.0"
        }

    def get_active_printer(self):
        if WIN32_READY:
            try:
                installed = printer_service.get_installed_printers()
                preferred = self.config["printer_name"]
                if preferred in installed:
                    return preferred
                default_p = win32print.GetDefaultPrinter()
                return default_p
            except Exception as e:
                logger.error(f"Error getting printer: {e}")
        return self.config["printer_name"]

    def get_installed_printers(self):
        if WIN32_READY:
            return printer_service.get_installed_printers()
        return ["Simulated Printer"]

    def send_heartbeat(self):
        now = time.time()
        if now - self.last_heartbeat < self.heartbeat_interval:
            return

        payload = {
            "printer_name": self.get_active_printer(),
            "status": "ONLINE",
            "installed_printers": self.get_installed_printers()
        }
        try:
            url = f"{self.server_url}/api/agent/heartbeat"
            resp = requests.post(url, json=payload, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                self.last_heartbeat = now
                logger.debug("Heartbeat sent successfully.")
            elif resp.status_code == 401:
                logger.error("Authentication failed: X-Agent-Secret does not match server AGENT_SECRET_KEY!")
            else:
                logger.warning(f"Heartbeat response HTTP {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            logger.warning(f"Failed to send heartbeat to {self.server_url}: {e}")

    def fetch_pending_jobs(self):
        url = f"{self.server_url}/api/agent/jobs"
        try:
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("jobs", [])
            elif resp.status_code == 401:
                logger.error("Agent secret rejected by server! Check AGENT_SECRET_KEY.")
            else:
                logger.warning(f"Fetch jobs HTTP {resp.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Error connecting to server {self.server_url}: {e}")
        return []

    def download_image(self, job_id, temp_dest):
        url = f"{self.server_url}/api/agent/download/{job_id}"
        resp = requests.get(url, headers=self.headers, stream=True, timeout=15)
        if resp.status_code == 200:
            with open(temp_dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        logger.error(f"Failed to download image for job {job_id}: HTTP {resp.status_code}")
        return False

    def update_job_status(self, job_id, status, error_message=""):
        url = f"{self.server_url}/api/agent/job/{job_id}/status"
        payload = {
            "status": status,
            "error_message": error_message
        }
        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=5)
            return resp.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Failed to update job {job_id} status: {e}")
            return False

    def process_job(self, job):
        job_id = job["id"]
        order_id = job["order_id"]
        copy_num = job.get("copy_number", 1)
        total_copies = job.get("total_copies", 1)
        paper_size = job.get("paper_size", "4x6")
        customer = job.get("customer_name", "Customer")

        logger.info(f"==> NEW JOB #{job_id}: Order {order_id} ({customer}) | Size: {paper_size} (Copy {copy_num}/{total_copies})")

        # 1. Mark as PRINTING
        self.update_job_status(job_id, "PRINTING")

        # 2. Download Image to Temp File
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_path = tmp.name

        try:
            download_ok = self.download_image(job_id, temp_path)
            if not download_ok:
                self.update_job_status(job_id, "FAILED", "Could not download image from cloud server")
                return

            # 3. Print Image to Spooler
            active_printer = self.get_active_printer()
            job_title = f"Photo Order {order_id[:8]} (Copy {copy_num}/{total_copies})"

            logger.info(f"Sending to printer '{active_printer}'...")
            if WIN32_READY:
                success, msg = printer_service.print_image(temp_path, job_title=job_title, printer_name=active_printer)
            else:
                logger.info(f"[SIMULATED PRINT] Emulating physical print...")
                time.sleep(3)
                success, msg = True, "Simulated print success"

            # 4. Report back completion
            if success:
                logger.info(f"Job #{job_id} Printed Successfully!")
                self.update_job_status(job_id, "COMPLETED")
            else:
                logger.error(f"Job #{job_id} Print Failed: {msg}")
                self.update_job_status(job_id, "FAILED", msg)

        except Exception as e:
            logger.error(f"Exception while executing job #{job_id}: {e}", exc_info=True)
            self.update_job_status(job_id, "FAILED", str(e))
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def run(self):
        logger.info("==================================================")
        logger.info("  Smart Photo Kiosk - Laptop Print Agent Started  ")
        logger.info("==================================================")
        logger.info(f"Target Hosted Server : {self.server_url}")
        logger.info(f"Assigned Printer     : {self.get_active_printer()}")
        logger.info(f"Polling Interval     : {self.poll_interval} seconds")
        logger.info("Waiting for paid orders from the cloud... (Press Ctrl+C to stop)")

        while True:
            try:
                self.send_heartbeat()
                jobs = self.fetch_pending_jobs()
                for job in jobs:
                    self.process_job(job)
            except KeyboardInterrupt:
                logger.info("Agent stopped by operator.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in agent main loop: {e}")

            time.sleep(self.poll_interval)


if __name__ == "__main__":
    agent = PrintAgent()
    agent.run()

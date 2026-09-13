# Free Cloud Hosting & Laptop Print Agent Guide

This guide explains how to host your Smart Photo Kiosk website online for **100% free** (permanent URL, permanent QR code, no tunneling needed) while keeping your Windows laptop connected to the Epson PM-520 printer via the new **Print Agent**.

---

## Architecture Overview

```
[Customer Smartphone]
        │
        ▼ (Any mobile data: 4G/5G/Wi-Fi)
[Cloud-Hosted Website] ── Free on Render.com (e.g., https://my-photo-booth.onrender.com)
        │ • Customer uploads photo (Standard or 8-Passport Grid)
        │ • Live preview, cropping & Razorpay payment
        │ • Enqueues paid job to cloud database
        ▼
[Encrypted Agent API]
        ▲
        │ (Polls every 3s via X-Agent-Secret)
[Laptop Print Agent] ──── Runs in background on Windows laptop (`run_agent.bat`)
        │
        ▼ (USB Cable)
[Epson PictureMate PM-520 Printer] (Silent, automatic printing)
```

---

## Step 1: Deploy Website to Render.com (Free)

1. Create a free account at [Render.com](https://render.com).
2. Push your project folder to a private GitHub / GitLab repository:
   ```bash
   git init
   git add .
   git commit -m "Photo kiosk cloud setup"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/photo-kiosk.git
   git push -u origin main
   ```
3. In Render Dashboard, click **New +** -> **Web Service**.
4. Select your GitHub repository.
5. Configure the service:
   * **Name**: `epson-photo-kiosk` (or your choice)
   * **Environment**: `Python 3`
   * **Region**: Choose closest to you (e.g., `Singapore` or `Frankfurt`)
   * **Branch**: `main`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   * **Instance Type**: **Free**
6. In **Environment Variables**, add:
   * `IS_CLOUD`: `true`
   * `AGENT_SECRET_KEY`: Choose any secure secret password (e.g. `kiosk-secret-2026`)
   * `RAZORPAY_KEY_ID`: Your Razorpay Key ID
   * `RAZORPAY_KEY_SECRET`: Your Razorpay Key Secret
   * `PASSPORT_PRICE`: `60.0` (Optional, defaults to 60 INR)
7. Click **Deploy Web Service**.
8. Once deployed, Render gives you a permanent HTTPS URL, for example:
   `https://epson-photo-kiosk.onrender.com`

---

## Step 2: Generate Permanent Poster QR Code

1. In your project directory on your laptop, open `generate_qr.py`.
2. Update the URL to your Render URL:
   ```python
   PORTAL_URL = "https://epson-photo-kiosk.onrender.com"
   ```
3. Run `python generate_qr.py`.
4. Your `kiosk_qr_code.png` is now permanent! You can print it on a standee, banner, or table sticker. It will **never change or expire**.

---

## Step 3: Run the Laptop Print Agent

On your Windows laptop connected to the Epson PM-520 via USB:

1. Open `agent_config.json` in your project folder:
   ```json
   {
     "server_url": "https://epson-photo-kiosk.onrender.com",
     "agent_secret": "kiosk-secret-2026",
     "printer_name": "EPSON PM-520 Series",
     "poll_interval_seconds": 3,
     "heartbeat_interval_seconds": 15
   }
   ```
   *(Make sure `server_url` matches your Render URL, and `agent_secret` matches your `AGENT_SECRET_KEY` from Step 1)*.

2. Double-click **`run_agent.bat`**.

3. You will see:
   ```
   ==================================================
     Smart Photo Kiosk - Laptop Print Agent Started  
   ==================================================
   Target Hosted Server : https://epson-photo-kiosk.onrender.com
   Assigned Printer     : EPSON PM-520 Series
   Polling Interval     : 3 seconds
   Waiting for paid orders from the cloud...
   ```

4. Go to `https://epson-photo-kiosk.onrender.com/admin`. The dashboard will display:
   **Laptop Agent: ONLINE (Connected)**.

---

## Step 4: Using the Passport Photo Feature

1. Open your website.
2. Click the top tab **"Passport Photos (8 Copies)"**.
3. Upload 1 portrait photo.
4. The cropping screen automatically locks to **3.5 cm × 4.5 cm** (7:9 ratio) and displays an oval face guideline.
5. Tap **Apply Framing**.
6. The system immediately renders the live **4×2 sheet preview** showing all 8 passport copies with cutting strokes.
7. Choose **Color** or **B&W**, pick number of sheets, and tap **Proceed to Pay**.
8. Once paid, the laptop print agent picks up the job and outputs the 8-photo passport sheet on the PM-520!

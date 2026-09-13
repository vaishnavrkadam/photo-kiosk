# Epson PM-520 Smart Photo Print & Kiosk System
## Step-by-Step Manual Setup & Operator Guide

This guide walks you through everything you need to do manually to set up your Epson PictureMate PM-520 printer, your Windows laptop, network access for customers' smartphones, and payment gateway configuration.

---

## 1. Epson PM-520 Printer Hardware & Driver Setup

### A. Unboxing & Hardware Verification
1. Place the Epson PM-520 on a stable, flat surface near your laptop or Wi-Fi router.
2. Install the ink cartridge provided with the printer.
3. Power on the printer and follow the initial ink charging on the printer's LCD screen (takes ~4-5 minutes).
4. Load photo paper into the rear feed slot:
   - Printable (glossy) side facing up.
   - Adjust the edge guides snugly against the paper edges without bending it.
   - Standard photo paper size for PM-520: **4 x 6 inches (10 x 15 cm)** or **5 x 7 inches (13 x 18 cm)**.

### B. Installing Official Windows Drivers
> [!IMPORTANT]
> Do **not** rely on basic generic Windows drivers. The official Epson driver is mandatory to support borderless photo printing, accurate DPI scaling, and paper profiles.

1. Download the official **Epson PM-520 Driver** for Windows 10/11 64-bit from Epson's official website:
   - [Epson Support - PictureMate PM-520](https://www.epson.co.in/Support/Printers/Photo-Printers/PictureMate-Series/Epson-PictureMate-PM-520/s/SPT_C11CD31501)
2. Run the downloaded installer (`.exe`).
3. Follow the on-screen prompts until you reach the connection selection screen:
   - Choose **USB Connection** (recommended for highest reliability and zero Wi-Fi drops), OR
   - Choose **Wireless (Wi-Fi) Connection** if you want the printer anywhere in the room.
4. Once completed, verify the printer appears in Windows:
   - Press `Win + R`, type `control printers`, and press Enter.
   - Look for **EPSON PM-520 Series**.
   - Right-click it -> **Printer Properties** -> click **Print Test Page** to verify physical connectivity.

### C. Setting Default Printing Preferences in Windows
To ensure silent, automated printing without print dialogues prompting the operator:
1. Open `control printers` (or Windows Settings -> Bluetooth & devices -> Printers & scanners -> EPSON PM-520 Series).
2. Click **Printing Preferences**.
3. Set the following defaults:
   - **Document Size**: `4 x 6 in (10 x 15 cm)` (or your preferred standard paper)
   - **Borderless**: Checked / Enabled (if you plan to print edge-to-edge photos)
   - **Orientation**: `Portrait`
   - **Paper Type**: `Epson Premium Glossy` or `Photo Paper Glossy`
   - **Quality**: `Standard` or `High`
   - **Color**: `Color`
4. Click **Apply** and **OK**.

---

## 2. Connectivity Options (Choose the Best for Your Setup)

You have 3 ways to connect the PM-520 to the laptop:

| Mode | Pros | Cons | Best For |
| :--- | :--- | :--- | :--- |
| **Option 1: USB Cable (Recommended)** | Zero latency, no network disconnections, 100% stable | Laptop must be wired to printer | Fixed kiosk booth, stall, event desk |
| **Option 2: Wi-Fi Router (Infrastructure)** | Laptop and printer both connect to same local Wi-Fi router | Depends on router stability | Office or venue with existing reliable Wi-Fi |
| **Option 3: Wi-Fi Direct** | Printer broadcasts its own direct Wi-Fi SSID | Laptop connects to printer's Wi-Fi; laptop may lose general internet unless using dual NIC | Standalone outdoor event without internet |

> **Recommendation**: Connect the printer to the laptop via **USB cable**. Have the laptop connect to Wi-Fi/Internet for the web app and payment processing. This eliminates any printing packet drops.

---

## 3. How Users Open the Website (Customer Smartphone Access)

Your customer will walk up, scan a QR code with their smartphone, and open the photo upload webpage. You have two options to expose the website:

### Option A: Local Network / Mobile Hotspot (Within 20–30 meters)
1. Connect your laptop to a Wi-Fi router or turn on **Mobile Hotspot** on your laptop/phone.
2. Have customers connect to that same Wi-Fi (e.g. "Free-Photo-Kiosk").
3. Find your laptop's local IP address:
   - Open PowerShell and run: `ipconfig`
   - Look for `IPv4 Address` (e.g., `192.168.1.45`).
4. Customers browse to `http://192.168.1.45:5000` (or generate a QR code pointing to this URL).

### Option B: Cloudflare Tunnel / ngrok (Recommended: Works on Mobile Data 4G/5G)
Customers don't need to join your Wi-Fi! They can scan the QR code and use their normal mobile data (Jio, Airtel, etc.):
1. Download [Cloudflare Tunnel (`cloudflared`)](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) or [ngrok](https://ngrok.com/).
2. Run:
   ```bash
   cloudflared tunnel --url http://localhost:5000
   ```
3. Cloudflare gives you a secure HTTPS URL (e.g., `https://instant-print-event.trycloudflare.com`).
4. Print this URL as a QR code poster on the printer table. Customers scan and upload immediately.

---

## 4. Payment Gateway Setup

The system includes a **Development / Test Simulation Mode** by default so you can test print immediately without spending money or waiting for payment approval.

To accept real customer payments:

### Option A: Razorpay (Standard for India - UPI, GPay, PhonePe, Cards)
1. Sign up at [razorpay.com](https://razorpay.com).
2. Complete KYC and go to **Settings -> API Keys**.
3. Generate **Key ID** and **Key Secret**.
4. In the project `.env` file, set:
   ```env
   PAYMENT_GATEWAY=razorpay
   RAZORPAY_KEY_ID=rzp_live_xxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
   ```
5. Customers will be able to pay seamlessly via Google Pay, PhonePe, Paytm, QR code, or Debit/Credit card.

### Option B: Dynamic UPI QR Code (Direct Bank Transfer / Zero Gateway Fees)
1. Generate an instant UPI payment intent string using your UPI VPA (e.g., `yourname@okaxis`, `yourbusiness@upi`).
2. The customer scans your UPI QR code from any UPI app and enters the exact amount.
3. System verifies payment via webhook / automated SMS listener / manual operator approve button.

### Option C: Stripe (International Support)
1. Sign up at [stripe.com](https://stripe.com).
2. Obtain `STRIPE_PUBLISHABLE_KEY` and `STRIPE_SECRET_KEY`.
3. Add to `.env`.

---

## 5. Daily Operation & Maintenance Checklist

### Before Starting the Event / Day:
1. **Paper Tray**: Load clean, uncurled 4x6" glossy paper (maximum 20-30 sheets at a time to prevent multi-sheet feeds).
2. **Ink Level**: Check the printer's LCD screen to ensure sufficient ink.
3. **Run Laptop Server**:
   - Double-click `run_kiosk.bat` on your desktop.
   - The terminal will launch the server and open the Operator Dashboard at `http://localhost:5000/admin`.
4. **Test Print**:
   - Click **"Test Print Sample"** from the Operator Dashboard.
   - Confirm the PM-520 wakes up and outputs a sharp, borderless test print.

### During Operation:
- The Operator Dashboard displays real-time jobs:
  - `QUEUED` -> `PRINTING` -> `COMPLETED` / `FAILED`
- If paper runs out:
  - The printer LCD will display "Paper Out".
  - Refill paper and press the printer's **OK** button.
  - The job resumes automatically.
- If a customer needs a reprint due to physical damage or smudge:
  - Operator clicks **"Reprint"** on that order ID from the dashboard without charging again.

---

## 6. Summary of Files & Steps We Will Create in This Project

1. **Backend Server (`app.py`)**:
   - Handles photo uploads with secure file validation.
   - Image crop/framing processor (preserves 3:2 aspect ratio for 4x6 paper).
   - Order creation & payment gateway integration (Razorpay / Stripe / Simulator).
   - Silent print queue worker interacting with Windows Print Spooler (`win32print` / SumatraPDF).
2. **Customer Web App (`frontend/`)**:
   - Mobile-responsive, sleek photo upload interface.
   - Interactive crop & live preview (Borderless, Polaroids, Borders, 4x6, 5x7).
   - Price calculation & instant checkout.
   - Real-time print status tracking ("Payment verified" -> "Printing photo 1 of 2" -> "Ready!").
3. **Admin / Operator Portal (`/admin`)**:
   - Queue management, reprint, paper counter, printer health check, price configuration.
4. **One-Click Launchers**:
   - `run_kiosk.bat` to launch the whole stack seamlessly with one double-click.

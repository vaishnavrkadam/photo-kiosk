import qrcode
import requests
import socket
import os

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_cloudflare_url():
    # Try cloudflared quicktunnel metrics on local port 20241
    try:
        res = requests.get("http://127.0.0.1:20241/quicktunnel", timeout=2)
        if res.status_code == 200:
            data = res.json()
            hostname = data.get("hostname")
            if hostname:
                return f"https://{hostname}"
    except Exception:
        pass
    return None

# Target Hosted URL for Photo Kiosk
DEPLOYED_URL = os.environ.get("KIOSK_PUBLIC_URL", "https://epson-photo-kiosk.onrender.com/")

def main():
    target_url = DEPLOYED_URL

    print("=" * 60)
    print(" EPSON PM-520 PHOTO KIOSK - ACCESS LINKS")
    print("=" * 60)
    print(f" [Live Cloud URL (Render.com)]:\n -> {target_url}")
    print("=" * 60)

    # Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(target_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    out_file = os.path.join(os.path.dirname(__file__), "kiosk_qr_code.png")
    img.save(out_file)
    print(f" QR Code image saved as: {out_file}")
    print(" You can open and scan this QR code with any smartphone camera!")
    print("=" * 60)

if __name__ == '__main__':
    main()

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

def main():
    cf_url = get_cloudflare_url()
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:5000"

    target_url = cf_url if cf_url else local_url

    print("=" * 60)
    print(" EPSON PM-520 PHOTO KIOSK - ACCESS LINKS")
    print("=" * 60)
    if cf_url:
        print(f" [Option B - Public Cloudflare Tunnel (4G/5G Worldwide)]:\n -> {cf_url}")
    print(f" [Option A - Local Wi-Fi Network URL]:\n -> {local_url}")
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

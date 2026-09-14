import os
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont
import config

TARGET_DPI = 300  # High-definition photo printing DPI

def get_target_pixel_dimensions(paper_size="4x6", landscape=False):
    """
    Returns (width_px, height_px) at 300 DPI for given paper size.
    For 4x6: 4 * 300 = 1200 px, 6 * 300 = 1800 px.
    """
    spec = config.PRICING.get(paper_size, config.PRICING["4x6"])
    width_in = spec["width_mm"] / 25.4
    height_in = spec["height_mm"] / 25.4
    
    w_px = int(round(width_in * TARGET_DPI))
    h_px = int(round(height_in * TARGET_DPI))
    
    if landscape:
        return max(w_px, h_px), min(w_px, h_px)
    else:
        return min(w_px, h_px), max(w_px, h_px)

def apply_sepia(image):
    """Converts PIL RGB image to vintage sepia tone."""
    gray = ImageOps.grayscale(image)
    # Sepia color tinting
    sepia = ImageOps.colorize(gray, black="#2e1f14", white="#fff3dc", mid="#a07a50")
    return sepia

def generate_passport_grid(raw_path, output_path, crop_box=None, color_mode="color", 
                           stroke_width=2, stroke_color=(200, 200, 200)):
    """
    Generates an 8-photo passport grid (4 cols x 2 rows) on a standard 4x6" landscape sheet (1800x1200 px at 300 DPI).
    Each individual passport photo is 3.5cm x 4.5cm (413x531 px) with a clean cutting border/stroke.
    """
    with Image.open(raw_path) as raw_img:
        img = ImageOps.exif_transpose(raw_img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        elif img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg

        # 1. Apply user crop (3.5 : 4.5 ratio)
        if crop_box:
            if len(crop_box) >= 5 and crop_box[4]:
                deg = int(crop_box[4])
                if deg != 0:
                    img = img.rotate(-deg, expand=True)
            x, y, w, h = [int(v) for v in crop_box[:4]]
            x = max(0, min(x, img.width - 1))
            y = max(0, min(y, img.height - 1))
            w = max(10, min(w, img.width - x))
            h = max(10, min(h, img.height - y))
            img = img.crop((x, y, x + w, y + h))

        # 2. Dimensions for 3.5cm x 4.5cm at 300 DPI
        photo_w = int(round((35.0 / 25.4) * TARGET_DPI))  # 413 px
        photo_h = int(round((45.0 / 25.4) * TARGET_DPI))  # 531 px

        # Fit into passport size
        passport_photo = ImageOps.fit(img, (photo_w, photo_h), method=Image.Resampling.LANCZOS)

        # Apply color filter
        if color_mode == "bw":
            passport_photo = ImageOps.grayscale(passport_photo).convert("RGB")
        elif color_mode == "sepia":
            passport_photo = apply_sepia(passport_photo)

        # 3. Add thin cutting stroke / border around the photo
        if stroke_width > 0:
            draw_border = ImageDraw.Draw(passport_photo)
            for s in range(stroke_width):
                draw_border.rectangle(
                    [s, s, photo_w - 1 - s, photo_h - 1 - s],
                    outline=stroke_color
                )

        # 4. Canvas: Standard 4x6" landscape sheet at 300 DPI (1800 x 1200 px)
        canvas_w, canvas_h = (1800, 1200)
        canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))

        # 4 columns x 2 rows = 8 photos
        cols = 4
        rows = 2
        col_gap = 20
        row_gap = 20

        total_grid_w = (cols * photo_w) + ((cols - 1) * col_gap)
        total_grid_h = (rows * photo_h) + ((rows - 1) * row_gap)

        start_x = max(0, (canvas_w - total_grid_w) // 2)
        start_y = max(0, (canvas_h - total_grid_h) // 2)

        # 5. Paste 8 copies into the 4x2 grid
        for r in range(rows):
            for c in range(cols):
                px = start_x + c * (photo_w + col_gap)
                py = start_y + r * (photo_h + row_gap)
                canvas.paste(passport_photo, (px, py))

        # 6. Save high-resolution 300 DPI print-ready image
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        canvas.save(output_path, format="JPEG", quality=96, dpi=(TARGET_DPI, TARGET_DPI))
        return output_path

def process_photo(raw_path, output_path, paper_size="4x6", layout_mode="borderless", 
                  color_mode="color", crop_box=None, caption="", landscape=False):
    """
    Processes the raw uploaded image into a print-ready 300 DPI image.
    If paper_size is 'passport', generates an 8-photo passport grid on 4x6 sheet.
    """
    if paper_size == "passport":
        return generate_passport_grid(
            raw_path=raw_path,
            output_path=output_path,
            crop_box=crop_box,
            color_mode=color_mode
        )

    # 1. Open and automatically rotate based on smartphone EXIF orientation
    with Image.open(raw_path) as raw_img:
        img = ImageOps.exif_transpose(raw_img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        elif img.mode == "RGBA":
            # Flatten transparency on white background
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
            
        # Determine orientation if not explicitly set
        if crop_box:
            # Crop box: [x, y, w, h] or [x, y, w, h, rotate]
            if len(crop_box) >= 5 and crop_box[4]:
                deg = int(crop_box[4])
                if deg != 0:
                    img = img.rotate(-deg, expand=True)
            x, y, w, h = [int(v) for v in crop_box[:4]]
            # Ensure within image bounds
            x = max(0, min(x, img.width - 1))
            y = max(0, min(y, img.height - 1))
            w = max(10, min(w, img.width - x))
            h = max(10, min(h, img.height - y))
            img = img.crop((x, y, x + w, y + h))
            is_landscape = (w > h)
        else:
            is_landscape = landscape or (img.width > img.height)
            
        target_w, target_h = get_target_pixel_dimensions(paper_size, landscape=is_landscape)
        
        # Apply color filter
        if color_mode == "bw":
            img = ImageOps.grayscale(img).convert("RGB")
        elif color_mode == "sepia":
            img = apply_sepia(img)
            
        # Canvas preparation
        canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
        
        if layout_mode == "borderless":
            # Scale to completely fill target canvas (Bleed fit)
            img_ratio = img.width / img.height
            target_ratio = target_w / target_h
            
            if img_ratio > target_ratio:
                # Image is wider: fit height and crop sides
                new_h = target_h
                new_w = int(round(img.width * (target_h / img.height)))
            else:
                # Image is taller: fit width and crop top/bottom
                new_w = target_w
                new_h = int(round(img.height * (target_w / img.width)))
                
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Center crop onto canvas
            offset_x = (new_w - target_w) // 2
            offset_y = (new_h - target_h) // 2
            canvas.paste(img_resized.crop((offset_x, offset_y, offset_x + target_w, offset_y + target_h)), (0, 0))
            
        elif layout_mode == "bordered":
            # Uniform 5mm white margin around edges (5mm at 300 DPI = ~59 px)
            margin = int(round((5.0 / 25.4) * TARGET_DPI))
            inner_w = target_w - (2 * margin)
            inner_h = target_h - (2 * margin)
            
            # Fit inside inner area
            img_fitted = ImageOps.fit(img, (inner_w, inner_h), method=Image.Resampling.LANCZOS)
            canvas.paste(img_fitted, (margin, margin))
            
        elif layout_mode == "polaroid":
            # Retro instant photo format:
            # Top, left, right margins ~8mm; bottom margin ~25mm
            margin_side = int(round((8.0 / 25.4) * TARGET_DPI))
            margin_bottom = int(round((28.0 / 25.4) * TARGET_DPI))
            
            inner_w = target_w - (2 * margin_side)
            inner_h = target_h - margin_side - margin_bottom
            
            img_fitted = ImageOps.fit(img, (inner_w, inner_h), method=Image.Resampling.LANCZOS)
            canvas.paste(img_fitted, (margin_side, margin_side))
            
            # Draw optional text caption on bottom white banner
            if caption and caption.strip():
                draw = ImageDraw.Draw(canvas)
                font_size = int(TARGET_DPI * 0.12)  # ~36pt
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()
                
                text = caption.strip()
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                text_x = (target_w - text_w) // 2
                text_y = target_h - margin_bottom + ((margin_bottom - text_h) // 2)
                draw.text((text_x, text_y), text, fill=(40, 40, 40), font=font)
        
        # Save high quality processed image
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        canvas.save(output_path, format="JPEG", quality=96, dpi=(TARGET_DPI, TARGET_DPI))
        return output_path

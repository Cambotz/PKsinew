import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import FONT_SOLID_PATH, SPRITES_DIR

# ----------------- SETTINGS -----------------

WIDTH, HEIGHT = 480, 320
GRID_THICKNESS = 2
LOGO_SCALE = 0.6

THEMES = {
    "firered": ((120, 10, 10), (220, 60, 30)),
    "leafgreen": ((20, 80, 20), (100, 180, 90)),
    "ruby": ((100, 0, 0), (200, 40, 40)),
    "sapphire": ((0, 40, 80), (40, 120, 200)),
    "emerald": ((0, 70, 50), (40, 200, 140)),
}

LOGO_PATH = os.path.join(SPRITES_DIR, "title", "SINEW.png")
OUT_DIR = os.path.join(SPRITES_DIR, "title")
os.makedirs(OUT_DIR, exist_ok=True)


# ----------------- BACKGROUNDS -----------------
def vertical_gradient(top, bottom):
    img = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=(*c, 255))
    return img


def draw_grid(img, cols=20, rows=14, thickness=2, color=(255, 255, 255, 40)):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    col_w = WIDTH / cols
    row_h = HEIGHT / rows
    for i in range(cols + 1):
        x = round(i * col_w)
        draw.rectangle((x, 0, min(x + thickness, WIDTH), HEIGHT), fill=color)
    for i in range(rows + 1):
        y = round(i * row_h)
        draw.rectangle((0, y, WIDTH, min(y + thickness, HEIGHT)), fill=color)
    img.alpha_composite(overlay)


def draw_scanlines(img):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, HEIGHT, 2):
        draw.line((0, y, WIDTH, y), fill=(0, 0, 0, 35))
    img.alpha_composite(overlay)


def draw_vignette(img):
    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(vignette)
    cx, cy = WIDTH / 2, HEIGHT / 2
    steps = 50
    for i in range(steps):
        alpha = int(80 * (i / steps) ** 2)
        bbox = [
            int(cx - cx * (i / steps)),
            int(cy - cy * (i / steps)),
            int(cx + cx * (i / steps)),
            int(cy + cy * (i / steps)),
        ]
        draw.ellipse(bbox, fill=alpha)
    vignette = vignette.filter(ImageFilter.GaussianBlur(15))
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay.putalpha(vignette)
    img.alpha_composite(overlay)


def draw_border(img, thickness=6, color=(255, 255, 255, 90)):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, WIDTH, thickness), fill=color)
    draw.rectangle((0, HEIGHT - thickness, WIDTH, HEIGHT), fill=color)
    draw.rectangle((0, 0, thickness, HEIGHT), fill=color)
    draw.rectangle((WIDTH - thickness, 0, WIDTH, HEIGHT), fill=color)
    img.alpha_composite(overlay)


# ----------------- LOGO / TEXT -----------------
def overlay_scanlines(img, x, y, w, h, opacity=50):
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for ly in range(0, h, 2):
        draw.line((0, ly, w, ly), fill=(0, 0, 0, opacity))
    img.alpha_composite(overlay, (x, y))


def paste_logo_or_text(bg, name):
    if name.lower() == "sinew":
        if not os.path.exists(LOGO_PATH):
            print("[!] Logo not found: %s" % LOGO_PATH)
            return
        logo = Image.open(LOGO_PATH).convert("RGBA")
        scale = (WIDTH * LOGO_SCALE) / logo.width
        logo = logo.resize(
            (int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS
        )
        x = (WIDTH - logo.width) // 2
        y = (HEIGHT - logo.height) // 3
        bg.alpha_composite(logo, (x, y))
        overlay_scanlines(bg, x, y, logo.width, logo.height, opacity=50)
    else:
        # Pokemon game names: uppercase, centered, black outline
        name = name.upper()
        font_size = 48

        # Check if font exists
        if not os.path.exists(FONT_SOLID_PATH):
            print("[!] Font not found: %s" % FONT_SOLID_PATH)
            print("    Using default font instead")
            font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(FONT_SOLID_PATH, font_size)

        bbox = font.getbbox(name)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = (WIDTH - text_w) // 2
        y = HEIGHT // 3 - text_h // 2

        outline_width = 2
        text_layer = Image.new(
            "RGBA",
            (text_w + outline_width * 2, text_h + outline_width * 2),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(text_layer)

        # Black outline
        offsets = [
            (dx, dy)
            for dx in range(-outline_width, outline_width + 1)
            for dy in range(-outline_width, outline_width + 1)
            if dx != 0 or dy != 0
        ]
        for ox, oy in offsets:
            draw.text(
                (outline_width + ox - bbox[0], outline_width + oy - bbox[1]),
                name,
                font=font,
                fill=(0, 0, 0, 255),
            )

        # Main white text
        draw.text(
            (outline_width - bbox[0], outline_width - bbox[1]),
            name,
            font=font,
            fill=(255, 255, 255, 255),
        )

        # Subtle scanlines on text
        scan_overlay = Image.new("RGBA", text_layer.size, (0, 0, 0, 0))
        scan_draw = ImageDraw.Draw(scan_overlay)
        for ly in range(0, text_layer.height, 2):
            scan_draw.line((0, ly, text_layer.width, ly), fill=(0, 0, 0, 25))
        text_layer.alpha_composite(scan_overlay)

        bg.alpha_composite(text_layer, (x - outline_width, y - outline_width))


# ----------------- WALLPAPER GENERATORS -----------------
def generate_game_wallpaper(name, colors):
    bg = vertical_gradient(*colors)
    draw_grid(bg)
    draw_scanlines(bg)
    draw_vignette(bg)
    draw_border(bg, thickness=6, color=(*colors[1], 120))
    paste_logo_or_text(bg, name)
    # Save as PNG but rename file to .gif
    out_path = os.path.join(OUT_DIR, "%s.gif" % name.lower())
    bg.save(out_path, format="PNG")
    print("[OK] %s generated" % out_path)


def generate_sinew_wallpaper():
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    for colors in THEMES.values():
        layer = vertical_gradient(*colors)
        layer.putalpha(50)
        bg.alpha_composite(layer)
    draw_grid(bg)
    draw_scanlines(bg)
    draw_vignette(bg)
    draw_border(bg, thickness=6, color=(255, 255, 255, 140))
    paste_logo_or_text(bg, "sinew")
    out_path = os.path.join(OUT_DIR, "PKSINEW.png")
    bg.save(out_path)
    print("[OK] %s generated" % out_path)


# ----------------- RUN -----------------
if __name__ == "__main__":
    print("Font path: %s" % FONT_SOLID_PATH)
    print("Output directory: %s" % OUT_DIR)
    print("")

    for game, colors in THEMES.items():
        if (ui := globals().get("ui_instance")) and ui.cancel_requested:
            break
        generate_game_wallpaper(game, colors)

    if not ((ui := globals().get("ui_instance")) and ui.cancel_requested):
        generate_sinew_wallpaper()
    print("")
    print("All wallpapers generated!")

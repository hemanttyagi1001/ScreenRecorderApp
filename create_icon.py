"""Generate a screen recorder app icon (screen_recorder.ico) using Pillow."""

from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]
BG_COLOR = (20, 30, 80)          # dark blue
MONITOR_COLOR = (40, 50, 110)    # slightly lighter blue for monitor
MONITOR_BORDER = (100, 120, 180) # light blue border
RECORD_COLOR = (220, 40, 40)     # red record button
RECORD_HIGHLIGHT = (255, 100, 100)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rectangle (full canvas with slight padding)
    pad = max(1, size // 16)
    draw.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=max(2, size // 6),
        fill=BG_COLOR,
    )

    # Monitor / screen rounded rectangle
    mx = max(2, size // 6)
    my = max(2, size // 5)
    draw.rounded_rectangle(
        [mx, my, size - mx, size - my - max(1, size // 8)],
        radius=max(1, size // 10),
        fill=MONITOR_COLOR,
        outline=MONITOR_BORDER,
        width=max(1, size // 32),
    )

    # Monitor stand (small rectangle below screen)
    stand_w = max(2, size // 5)
    stand_h = max(1, size // 16)
    stand_x = (size - stand_w) // 2
    stand_y = size - my - max(1, size // 8) + 1
    draw.rectangle(
        [stand_x, stand_y, stand_x + stand_w, stand_y + stand_h],
        fill=MONITOR_BORDER,
    )

    # Base of the stand
    base_w = max(4, size // 3)
    base_h = max(1, size // 20)
    base_x = (size - base_w) // 2
    base_y = stand_y + stand_h
    draw.rounded_rectangle(
        [base_x, base_y, base_x + base_w, base_y + base_h],
        radius=max(1, base_h // 2),
        fill=MONITOR_BORDER,
    )

    # Red record circle centered in the monitor screen area
    screen_cx = size // 2
    screen_top = my + max(1, size // 32)
    screen_bottom = size - my - max(1, size // 8) - max(1, size // 32)
    screen_cy = (screen_top + screen_bottom) // 2
    radius = max(2, (screen_bottom - screen_top) // 3)

    draw.ellipse(
        [screen_cx - radius, screen_cy - radius,
         screen_cx + radius, screen_cy + radius],
        fill=RECORD_COLOR,
    )

    # Small highlight on the record button
    hr = max(1, radius // 3)
    hx = screen_cx - radius // 4
    hy = screen_cy - radius // 4
    draw.ellipse(
        [hx - hr, hy - hr, hx + hr, hy + hr],
        fill=RECORD_HIGHLIGHT,
    )

    return img


def main():
    images = [draw_icon(s) for s in SIZES]
    output_path = "d:/Code/hemanttyagi-screen-recorder-tool/screen_recorder.ico"
    # The largest image is used as the base; append_images provides the rest.
    # Pillow ICO plugin needs the images passed and will encode each one.
    largest = images[-1]  # 256x256
    rest = images[:-1]
    largest.save(
        output_path,
        format="ICO",
        append_images=rest,
    )
    print(f"Icon saved: {output_path}")
    for s in SIZES:
        print(f"  - {s}x{s}")


if __name__ == "__main__":
    main()

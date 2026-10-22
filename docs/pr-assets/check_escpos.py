"""What an ESC/POS printer receives for Arabic text, decoded back to pixels.

Prints through python-escpos' Dummy printer (TM-T88V profile, 512 dots) and
decodes every ``GS v 0`` raster block in the output into an image, which is
exactly what the printer would put on paper.

Usage: python check_escpos.py OUT_DIR
"""

import sys
from importlib.metadata import version
from pathlib import Path

import khatt
from escpos.printer import Dummy
from PIL import Image

TEXT = "عصير برتقال  ٢٥ ج.م\nشكرًا لزيارتكم"


def rasters(data: bytes) -> Image.Image:
    """Stack the GS v 0 raster blocks of an ESC/POS byte stream."""
    blocks, i = [], 0
    while (i := data.find(b"\x1dv0", i)) != -1:
        width_bytes = data[i + 4] + 256 * data[i + 5]
        height = data[i + 6] + 256 * data[i + 7]
        bits = data[i + 8 : i + 8 + width_bytes * height]
        # In GS v 0 a set bit is a black dot; mode "1" uses 1 for white.
        blocks.append(
            Image.frombytes(
                "1", (width_bytes * 8, height), bytes(255 - b for b in bits)
            )
        )
        i += 8 + width_bytes * height
    sheet = Image.new(
        "1", (max(b.width for b in blocks), sum(b.height for b in blocks)), 1
    )
    y = 0
    for block in blocks:
        sheet.paste(block, (0, y))
        y += block.height
    return sheet


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    p = Dummy(profile="TM-T88V")
    width = int(p.profile.profile_data["media"]["width"]["pixels"])
    print("escpos", version("python-escpos"), "khatt", version("khatt"), "width", width)

    for font in ("noto-naskh", "cairo"):
        img = khatt.caption_image(
            TEXT,
            font=font,
            font_size=30,
            size=(width, None),
            method="caption",
            bg_color="white",
        )
        print(font, img.size, img.mode)
        p = Dummy(profile="TM-T88V")
        p.image(img)
        rasters(p.output).save(out / f"printed_{font}.png")

    t = Dummy(profile="TM-T88V")
    t.text("عصير\n")
    print("text() bytes:", t.output)


if __name__ == "__main__":
    main(Path(sys.argv[1]))

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def make_png(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    def chunk(typ: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(rgba) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


for size in (192, 512):
    (OUT / f"icon-{size}.png").write_bytes(make_png(size, size, (37, 99, 235, 255)))
    print("wrote", OUT / f"icon-{size}.png")
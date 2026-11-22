"""
Rampage / SinoWealth (258A:0016) RGB keyboard protocol.

The firmware keeps its lighting state in 1032-byte "pages" that are read and
written through HID feature reports:

* Report 5 (6 bytes)    -> command channel. ``05 8X <addr> 00 <len> 00`` asks
                           the keyboard to load page ``addr`` for reading.
* Report 6 (1032 bytes) -> data channel. A GET returns the requested page, a
                           SET writes a page (``06 0X <addr> 00 <len> 00 ...``).

Pages used here:

* Config page  (cmd 0x03, addr 0xB6)
    [20]          per-key (custom) mode flag
    [21]          active mode id (0 = off, 1..20 = effects)
    [22]          0x20 | custom preset
    [36 + 2*m]    mode m colour byte: bits 0-2 colour preset (0..6, 7 = random/
                  colourful), bit 7 = direction (1 = left)
    [37 + 2*m]    mode m packed byte: (speed << 4) | brightness, both 0..4
* Colour page  (cmd 0x08, addr 0xB8)
    [8 + 21*m + 3*p .. +2]   mode m, preset p (0..6) colour as R, G, B

Offsets were derived from the captured vendor-software templates in
``templates/`` (they differ only in the bytes listed above) and match the
layout documented by the OpenRGB project for SinoWealth keyboards.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

VID = 0x258A
PID = 0x0016
LIGHTING_USAGE = 128
LIGHTING_USAGE_PAGE = 1

REPORT_ID_CMD = 0x05
REPORT_ID_DATA = 0x06
CMD_LEN = 6
PAYLOAD_LEN = 1032

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

# Page descriptors: (write command, address, length byte)
PAGE_CONFIG = (0x03, 0xB6, 0x00)
PAGE_COLORS = (0x08, 0xB8, 0x40)

# SinoWealth boards sharing 258A:0016 use the same page layout but different
# page addresses. Reads work at either address on the tested keyboard, so the
# only reliable way to find the right variant is write + read back.
VARIANTS: Dict[str, Dict[str, Any]] = {
    "kb16": {
        "title": "SinoWealth 0016 (OpenRGB 'Keyboard16')",
        "config": (0x03, 0x00, 0x00),
        "colors": (0x08, 0xA8, 0x40),
        "init": bytes([0x05, 0x01, 0xAA, 0xBB, 0x2F, 0x3E]),
    },
    "f11": {
        "title": "SinoWealth F11 şablonu (eski uygulama)",
        "config": PAGE_CONFIG,
        "colors": PAGE_COLORS,
        "init": None,
    },
}
DEFAULT_VARIANT = "kb16"

IDX_PER_KEY = 20
IDX_MODE = 21
IDX_CUSTOM = 22
IDX_MAGIC = 14            # 0x5A 0xA5 marks a valid config page
MODE_SLOT_BASE = 36       # colour byte of mode m = 36 + 2m, packed byte = 37 + 2m
COLOR_BASE = 8
COLORS_PER_MODE = 7
COLOR_RANDOM = 7          # "colourful" / random colour option

MAX_LEVEL = 4             # speed and brightness are 0..4

# id: (key, Turkish title, short description, flags)
# flags: s = speed, c = colour selectable, d = direction
_MODE_TABLE = [
    (0, "off", "Kapalı", "Tüm LED'ler sönük", ""),
    (1, "static", "Sabit Renk", "Tek renk, sabit ışık", "c"),
    (2, "breathing", "Nefes", "Yavaşça yanıp sönen ışık", "sc"),
    (3, "rainbow", "Gökkuşağı Dalgası", "Klavye boyunca akan spektrum", "sd"),
    (4, "flash_away", "Kaybolan Işık", "Basılan tuştan yayılıp sönen ışık", "sc"),
    (5, "raindrops", "Yağmur Damlaları", "Rastgele düşen ışık damlaları", "sc"),
    (6, "rainbow_wheel", "Gökkuşağı Çarkı", "Merkez etrafında dönen spektrum", "sd"),
    (7, "ripples", "Dalgacıklar", "Basılan tuştan yayılan halkalar", "sc"),
    (8, "stars", "Yıldız Pırıltısı", "Rastgele parlayan tuşlar", "sc"),
    (9, "shadow", "Gölge", "Basılan tuş yanar, sonra kaybolur", "sc"),
    (10, "snake", "Retro Yılan", "Tuşlar üzerinde gezen yılan", "scd"),
    (11, "neon", "Neon Akış", "Tüm klavyede yavaş renk geçişi", "s"),
    (12, "reaction", "Tepki", "Basılan tuşu aydınlatır", "sc"),
    (13, "sine_wave", "Sinüs Dalgası", "Dalgalanan parlaklık", "scd"),
    (14, "scanning", "Tarama", "Soldan sağa tarayan çizgi", "scd"),
    (15, "windmill", "Yel Değirmeni", "Dönen ışık kanatları", "scd"),
    (16, "waterfall", "Renkli Şelale", "Yukarıdan aşağı akan renkler", "sd"),
    (17, "blossom", "Çiçeklenme", "Merkezden açılan renkler", "sc"),
    (18, "storm", "Dönen Fırtına", "Spiral şeklinde dönen renkler", "scd"),
    (19, "collision", "Çarpışma", "İki uçtan gelip çarpışan ışıklar", "sc"),
    (20, "perfect", "Kusursuz", "Renk döngüsü", "s"),
]

MODES: Dict[int, Dict[str, Any]] = {
    mid: {
        "id": mid,
        "name": key,
        "title": title,
        "description": desc,
        "has_speed": "s" in flags,
        "has_brightness": mid != 0,
        "has_color": "c" in flags,
        "has_direction": "d" in flags,
    }
    for mid, key, title, desc, flags in _MODE_TABLE
}

MODE_BY_NAME: Dict[str, int] = {m["name"]: mid for mid, m in MODES.items()}
MODE_BY_NAME.update({
    # Aliases kept for older profiles / CLI habits
    "red": 1, "kırmızı": 1, "sabit": 1,
    "spectrum": 3, "gökkuşağı": 3, "wave": 3,
    "wheel": 6, "star": 8, "star_twinkle": 8,
    "yılan": 10, "retro_snake": 10,
    "sine": 13, "rainbow_blossom": 17, "blossoming": 17,
    "kapalı": 0, "kapat": 0,
})

DEFAULT_PALETTE = ["#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#FF00FF", "#00FFFF", "#FFFFFF"]

_TEMPLATE_CACHE: Dict[str, List[List[int]]] = {}


def resolve_mode(mode: Union[int, str, None]) -> int:
    """Map a mode id or name to a valid mode id (raises ValueError)."""
    if mode is None:
        raise ValueError("Mod belirtilmedi")
    if isinstance(mode, str):
        text = mode.strip().lower()
        if text.isdigit():
            mode = int(text)
        elif text in MODE_BY_NAME:
            return MODE_BY_NAME[text]
        else:
            raise ValueError(f"Bilinmeyen mod: {mode}")
    mid = int(mode)
    if mid not in MODES:
        raise ValueError(f"Geçersiz mod numarası: {mid}")
    return mid


def clamp_level(value: Any, default: int) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(MAX_LEVEL, v))


def parse_hex_color(value: str) -> Tuple[int, int, int]:
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        raise ValueError(f"Geçersiz renk: {value}")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


# --------------------------------------------------------------------------
# Command / page helpers
# --------------------------------------------------------------------------

def read_request(page: Tuple[int, int, int]) -> bytes:
    """6-byte report-5 command that loads ``page`` for a following GET."""
    cmd, addr, length = page
    return bytes([REPORT_ID_CMD, cmd | 0x80, addr, 0x00, length, 0x00])


# The firmware may answer with fewer bytes than the full page (the config page
# comes back as 80 bytes on macOS). These are the minimum useful lengths.
MIN_READ = {
    0x03: MODE_SLOT_BASE + 2 * 21,                 # config: through mode 20's slot
    0x08: COLOR_BASE + COLORS_PER_MODE * 3 * 21,   # colours: through mode 20's palette
}


def normalize_read(page: Tuple[int, int, int], raw: bytes, base: bytes) -> Optional[bytearray]:
    """Overlay a (possibly short) page read from the keyboard onto ``base``.

    Returns None when the answer is too short to be useful.
    """
    cmd, addr, length = page
    if len(raw) < MIN_READ[cmd]:
        return None
    buf = bytearray(base)
    buf[: min(len(raw), PAYLOAD_LEN)] = raw[:PAYLOAD_LEN]
    buf[0] = REPORT_ID_DATA
    buf[1] = cmd
    buf[2] = addr
    buf[3] = 0x00
    buf[4] = length
    buf[5] = 0x00
    return buf


def is_valid_config(page: Optional[bytes]) -> bool:
    return (
        page is not None
        and len(page) == PAYLOAD_LEN
        and page[IDX_MAGIC] == 0x5A
        and page[IDX_MAGIC + 1] == 0xA5
        and page[IDX_MODE] in MODES
    )


def is_valid_colors(page: Optional[bytes]) -> bool:
    return page is not None and len(page) == PAYLOAD_LEN and page[0] == REPORT_ID_DATA


def _template(name: str) -> List[List[int]]:
    if name not in _TEMPLATE_CACHE:
        with open(TEMPLATE_DIR / f"{name}.json", "r", encoding="utf-8") as f:
            _TEMPLATE_CACHE[name] = json.load(f)
    return _TEMPLATE_CACHE[name]


def default_config_page() -> bytearray:
    """Known-good config page captured from the vendor software."""
    return bytearray(_template("fw-static")[4])


def default_colors_page() -> bytearray:
    """Known-good colour page captured from the vendor software."""
    return bytearray(_template("fw-static")[1])


# --------------------------------------------------------------------------
# Config page encode / decode
# --------------------------------------------------------------------------

def _slot(mode_id: int) -> Tuple[int, int]:
    color_idx = MODE_SLOT_BASE + 2 * mode_id
    return color_idx, color_idx + 1


def get_mode_settings(config: bytes, mode_id: int) -> Dict[str, Any]:
    if mode_id == 0:
        return {"speed": 0, "brightness": 0, "color": 0, "direction_left": False}
    ci, pi = _slot(mode_id)
    color_byte, packed = config[ci], config[pi]
    return {
        "speed": min(MAX_LEVEL, packed >> 4),
        "brightness": min(MAX_LEVEL, packed & 0x0F),
        "color": color_byte & 0x07,
        "direction_left": bool(color_byte & 0x80),
    }


def build_config_page(
    base: bytes,
    mode_id: int,
    speed: Optional[int] = None,
    brightness: Optional[int] = None,
    color: Optional[int] = None,
    direction_left: Optional[bool] = None,
    page_desc: Tuple[int, int, int] = PAGE_CONFIG,
) -> bytearray:
    """Return a copy of ``base`` switched to ``mode_id`` with the given settings.

    Settings left as ``None`` keep the value stored on the keyboard.
    """
    page = bytearray(base)
    page[0:6] = bytes([REPORT_ID_DATA, page_desc[0], page_desc[1], 0, page_desc[2], 0])
    page[IDX_PER_KEY] = 0
    page[IDX_MODE] = mode_id
    if page[IDX_CUSTOM] & 0xF0 != 0x20:
        page[IDX_CUSTOM] = 0x20

    if mode_id == 0:
        return page

    current = get_mode_settings(page, mode_id)
    speed = current["speed"] if speed is None else clamp_level(speed, current["speed"])
    brightness = current["brightness"] if brightness is None else clamp_level(brightness, current["brightness"])
    color = current["color"] if color is None else max(0, min(COLOR_RANDOM, int(color)))
    direction_left = current["direction_left"] if direction_left is None else bool(direction_left)

    ci, pi = _slot(mode_id)
    page[ci] = (page[ci] & 0x78) | (color & 0x07) | (0x80 if direction_left else 0)
    page[pi] = ((speed & 0x0F) << 4) | (brightness & 0x0F)
    return page


# --------------------------------------------------------------------------
# Colour page encode / decode
# --------------------------------------------------------------------------

def _color_offset(mode_id: int, preset: int) -> int:
    return COLOR_BASE + COLORS_PER_MODE * 3 * mode_id + 3 * preset


def get_palette(colors: bytes, mode_id: int) -> List[str]:
    out = []
    for p in range(COLORS_PER_MODE):
        o = _color_offset(mode_id, p)
        out.append(to_hex(colors[o], colors[o + 1], colors[o + 2]))
    return out


def build_colors_page(
    base: bytes, mode_id: int, palette: Dict[int, str],
    page_desc: Tuple[int, int, int] = PAGE_COLORS,
) -> bytearray:
    """Return a copy of ``base`` with ``palette`` ({preset: '#RRGGBB'}) set for ``mode_id``."""
    page = bytearray(base)
    page[0:6] = bytes([REPORT_ID_DATA, page_desc[0], page_desc[1], 0, page_desc[2], 0])
    for preset, value in palette.items():
        preset = int(preset)
        if not 0 <= preset < COLORS_PER_MODE:
            raise ValueError(f"Geçersiz renk yuvası: {preset}")
        r, g, b = parse_hex_color(value)
        o = _color_offset(mode_id, preset)
        page[o], page[o + 1], page[o + 2] = r, g, b
    return page


def describe_state(config: bytes, colors: bytes) -> Dict[str, Any]:
    """Human-readable lighting state decoded from the two pages."""
    mode_id = config[IDX_MODE] if config[IDX_MODE] in MODES else 0
    settings = get_mode_settings(config, mode_id)
    info = MODES[mode_id]
    per_key = bool(config[IDX_PER_KEY])
    custom_preset = (config[IDX_CUSTOM] & 0x0F) + 1
    return {
        "mode": mode_id,
        "mode_name": "custom" if per_key else info["name"],
        "mode_title": f"Özel tuş profili {custom_preset}" if per_key else info["title"],
        "per_key": per_key,
        "custom_preset": custom_preset,
        **settings,
        "palette": get_palette(colors, mode_id) if mode_id else list(DEFAULT_PALETTE),
        "modes": {
            mid: {**get_mode_settings(config, mid), "palette": get_palette(colors, mid)}
            for mid in MODES if mid
        },
    }

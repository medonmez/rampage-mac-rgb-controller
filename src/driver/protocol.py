"""
Rampage / SinoWealth (258A:0016) RGB keyboard protocol.

The firmware keeps its lighting state in 1032-byte "pages" that are read and
written through HID feature reports:

* Report 5 (6 bytes)    -> command channel. ``05 8X <addr> 00 <len> 00`` asks
                           the keyboard to load a page for reading;
                           ``05 01 AA BB 2F 3E`` initialises the session.
* Report 6 (1032 bytes) -> data channel. A GET returns the requested page, a
                           SET writes a page (``06 0X <addr> 00 <len> 00 ...``).

Pages (verified on the keyboard by write + read back):

* Config page  (write ``06 03 00 00 00 00``)
    [14:16]       0x5A 0xA5 magic
    [20]          1 = a custom per-key profile is active
    [21]          active mode id (0 = off, 1..14 effects, 0x0F custom)
    [22]          0x20 | custom profile index (0..4)
    [32 + 2*m]    mode m colour byte: bits 0-2 colour preset (0..6, 7 = random),
                  bit 7 = direction (1 = left)
    [33 + 2*m]    mode m packed byte: (speed << 4) | brightness, both 0..4
* Colour page  (write ``06 08 A8 00 40 00``)
    [8 + 21*m + 3*p .. +2]   mode m, preset p (0..6) colour as B, G, R

The mode list and offsets follow OpenRGB's SinowealthKeyboard16 controller,
which targets this USB id, and match what the keyboard shows for each id.
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
PAGE_CONFIG = (0x03, 0x00, 0x00)
PAGE_COLORS = (0x08, 0xA8, 0x40)
INIT_COMMAND = bytes([0x05, 0x01, 0xAA, 0xBB, 0x2F, 0x3E])

VARIANTS: Dict[str, Dict[str, Any]] = {
    "kb16": {
        "title": "SinoWealth 0016",
        "config": PAGE_CONFIG,
        "colors": PAGE_COLORS,
        "init": INIT_COMMAND,
    },
}
DEFAULT_VARIANT = "kb16"

IDX_PER_KEY = 20
IDX_MODE = 21
IDX_CUSTOM = 22
IDX_MAGIC = 14            # 0x5A 0xA5 marks a valid config page
MODE_SLOT_BASE = 32       # colour byte of mode m = 32 + 2m, packed byte = 33 + 2m
COLOR_BASE = 8
COLORS_PER_MODE = 7
COLOR_RANDOM = 7          # "colourful" / random colour option
MODE_CUSTOM = 0x0F        # per-key custom profiles (CM1..CM5, Fn+1..5)
CUSTOM_PROFILES = 5

MAX_LEVEL = 4             # speed and brightness are 0..4

# id: (key, Turkish title, short description, flags)
# flags: s = speed, c = colour selectable, d = direction, r = reacts to key presses,
#        x = listed by OpenRGB but shows nothing on the Rampage keyboard (hidden)
_MODE_TABLE = [
    (0, "off", "Kapalı", "Tüm LED'ler sönük", ""),
    (1, "color_cycle", "Renk Döngüsü", "Tüm klavye renkten renge geçer", "s"),
    (2, "breathing", "Nefes", "Yavaşça yanıp sönen ışık", "sc"),
    (3, "static", "Sabit Renk", "Tek renk, sabit ışık", "c"),
    (4, "ripples", "Dalgacıklar", "Basılan tuştan halkalar yayılır", "scrx"),
    (5, "reaction", "Tepki", "Basılan tuş yanıp söner", "scr"),
    (6, "flash_away", "Kaybolan Işık", "Basılan tuştan ışık yayılıp kaybolur", "scrx"),
    (7, "sine_wave", "Sinüs Dalgası", "Klavye boyunca dalgalanan ışık", "sc"),
    (8, "raindrops", "Yağmur Damlaları", "Rastgele parlayan damlalar", "sc"),
    (9, "rainbow", "Gökkuşağı Dalgası", "Klavye boyunca akan spektrum", "sd"),
    (10, "rainbow_wheel", "Gökkuşağı Çarkı", "Merkez etrafında dönen spektrum", "sd"),
    (11, "adorn", "Süsleme", "Hareketli renk deseni", "s"),
    (12, "stars", "Yıldız Pırıltısı", "Rastgele parlayan tuşlar", "sc"),
    (13, "shadow", "Gölge", "Basılan tuş söner, sonra geri gelir", "scr"),
    (14, "snake", "Retro Yılan", "Tuşlar üzerinde gezen yılan", "sc"),
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
        "reactive": "r" in flags,
        "supported": "x" not in flags,
    }
    for mid, key, title, desc, flags in _MODE_TABLE
}

MODE_BY_NAME: Dict[str, int] = {m["name"]: mid for mid, m in MODES.items()}
MODE_BY_NAME.update({
    # Aliases kept for older profiles / CLI habits
    "red": 3, "kırmızı": 3, "sabit": 3, "color_loop": 1, "neon": 1, "neon_stream": 1,
    "spectrum": 9,
    "gökkuşağı": 9, "wave": 9, "wheel": 10,
    "star": 12, "star_twinkle": 12, "yılan": 14, "retro_snake": 14,
    "sine": 7, "nefes": 2, "respire": 2,
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
    0x03: MODE_SLOT_BASE + 2 * len(MODES),                 # config: all mode slots
    0x08: COLOR_BASE + COLORS_PER_MODE * 3 * len(MODES),   # colours: all palettes
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
        and (page[IDX_MODE] in MODES or page[IDX_MODE] == MODE_CUSTOM or page[IDX_PER_KEY])
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


def is_custom(config: bytes) -> bool:
    return bool(config[IDX_PER_KEY]) or config[IDX_MODE] == MODE_CUSTOM


def build_custom_page(base: bytes, profile: int, page_desc: Tuple[int, int, int] = PAGE_CONFIG) -> bytearray:
    """Switch to the keyboard's stored per-key custom profile ``profile`` (0..4)."""
    if not 0 <= profile < CUSTOM_PROFILES:
        raise ValueError(f"Özel profil 1-{CUSTOM_PROFILES} arasında olmalı")
    page = bytearray(base)
    page[0:6] = bytes([REPORT_ID_DATA, page_desc[0], page_desc[1], 0, page_desc[2], 0])
    page[IDX_PER_KEY] = 1
    page[IDX_MODE] = MODE_CUSTOM
    page[IDX_CUSTOM] = 0x20 | profile
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
        # stored as B, G, R
        out.append(to_hex(colors[o + 2], colors[o + 1], colors[o]))
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
        page[o], page[o + 1], page[o + 2] = b, g, r  # firmware order is B, G, R
    return page


def describe_state(config: bytes, colors: bytes) -> Dict[str, Any]:
    """Human-readable lighting state decoded from the two pages."""
    per_key = is_custom(config)
    mode_id = config[IDX_MODE] if config[IDX_MODE] in MODES else 0
    settings = get_mode_settings(config, 0 if per_key else mode_id)
    info = MODES[mode_id]
    custom_preset = (config[IDX_CUSTOM] & 0x0F) + 1
    return {
        "mode": MODE_CUSTOM if per_key else mode_id,
        "mode_name": "custom" if per_key else info["name"],
        "mode_title": f"Özel tuş profili {custom_preset}" if per_key else info["title"],
        "per_key": per_key,
        "custom_preset": custom_preset,
        **settings,
        "palette": get_palette(colors, mode_id) if mode_id and not per_key else list(DEFAULT_PALETTE),
        "modes": {
            mid: {**get_mode_settings(config, mid), "palette": get_palette(colors, mid)}
            for mid in MODES if mid
        },
    }

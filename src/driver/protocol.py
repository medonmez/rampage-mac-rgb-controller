"""
Rampage / SinoWealth (258A:0016) RGB Keyboard Protocol Definitions.
Focused, verified hardware burst profiles for confirmed working modes.
"""
import os
import json
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional, Union

VID = 0x258A
PID = 0x0016
LIGHTING_USAGE = 128
LIGHTING_USAGE_PAGE = 1

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

# 100% Verified Working Hardware Modes
MODES = {
    1: {"id": 1, "name": "rainbow", "template": "fw-rainbow", "title": "Gökkuşağı Dalgası (Rainbow Wave)", "has_speed": True, "has_brightness": True},
    2: {"id": 2, "name": "static", "template": "fw-static", "title": "Sabit Kırmızı (Static Red)", "has_speed": False, "has_brightness": True},
    3: {"id": 3, "name": "snake", "template": "fw-snake", "title": "Retro Yılan (Retro Snake)", "has_speed": True, "has_brightness": True},
    0: {"id": 0, "name": "off", "template": "fw-static", "title": "Işıkları Kapat (Off)", "has_speed": False, "has_brightness": False},
}

MODE_BY_NAME = {
    "rainbow": 1,
    "spectrum": 1,
    "gökkuşağı": 1,
    "static": 2,
    "red": 2,
    "kırmızı": 2,
    "snake": 3,
    "yılan": 3,
    "retro_snake": 3,
    "off": 0,
    "kapalı": 0,
}

_CACHED_TEMPLATES: Dict[str, List[List[int]]] = {}

def _get_template(name: str) -> List[List[int]]:
    global _CACHED_TEMPLATES
    if name not in _CACHED_TEMPLATES:
        path = TEMPLATE_DIR / f"{name}.json"
        if not path.exists():
            path = TEMPLATE_DIR / "fw-static.json"
        with open(path, "r", encoding="utf-8") as f:
            _CACHED_TEMPLATES[name] = json.load(f)
    return _CACHED_TEMPLATES[name]


def encode_effect_burst(
    mode: Union[int, str],
    speed: int = 2,
    brightness: int = 4
) -> List[bytes]:
    """
    Encode a full 5-frame burst (Handshake + 4 Data Blocks) for the keyboard.
    - mode: 1 (rainbow), 2 (static red), 3 (snake), 0 (off)
    - speed: 0..4 (0=slowest, 4=fastest)
    - brightness: 0..4 (0=off, 4=max)
    """
    if isinstance(mode, str):
        mode_id = MODE_BY_NAME.get(mode.lower(), 1)
    else:
        mode_id = int(mode)

    mode_info = MODES.get(mode_id, MODES[1])
    template_name = mode_info["template"]
    raw_template = _get_template(template_name)

    frames = [bytearray(f) for f in raw_template]

    if mode_id == 0:  # OFF
        brightness = 0

    speed = max(0, min(4, int(speed)))
    brightness = max(0, min(4, int(brightness)))

    # Frame 4 (Block 4): Patch speed and brightness at offsets 69 and 71
    packed_sb = ((speed & 0x0F) << 4) | (brightness & 0x0F)
    if len(frames) > 4 and len(frames[4]) > 71:
        frames[4][69] = packed_sb
        frames[4][71] = packed_sb

    return [bytes(f) for f in frames]

"""
Rampage RGB Driver Package.
"""
from .protocol import (
    VID, PID, LIGHTING_USAGE, LIGHTING_USAGE_PAGE,
    MODES, MODE_BY_NAME,
    encode_effect_burst
)
from .layout import KEYBOARD_LAYOUT, KEY_GROUPS
from .iokit_driver import RampageKeyboardDriver, get_driver

__all__ = [
    "VID", "PID", "LIGHTING_USAGE", "LIGHTING_USAGE_PAGE",
    "MODES", "MODE_BY_NAME",
    "encode_effect_burst",
    "KEYBOARD_LAYOUT", "KEY_GROUPS",
    "RampageKeyboardDriver", "get_driver"
]

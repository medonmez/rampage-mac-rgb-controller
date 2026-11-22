"""
Rampage RGB driver package.
"""
from .protocol import (
    VID, PID, LIGHTING_USAGE, LIGHTING_USAGE_PAGE,
    MODES, MODE_BY_NAME, DEFAULT_PALETTE, COLOR_RANDOM, MAX_LEVEL,
    resolve_mode,
)
from .layout import KEYBOARD_LAYOUT, KEY_GROUPS
from .iokit_driver import RampageKeyboardDriver, DeviceError, get_driver

__all__ = [
    "VID", "PID", "LIGHTING_USAGE", "LIGHTING_USAGE_PAGE",
    "MODES", "MODE_BY_NAME", "DEFAULT_PALETTE", "COLOR_RANDOM", "MAX_LEVEL",
    "resolve_mode",
    "KEYBOARD_LAYOUT", "KEY_GROUPS",
    "RampageKeyboardDriver", "DeviceError", "get_driver",
]

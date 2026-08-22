"""
macOS IOKit HID Driver for SinoWealth (258A:0016) RGB Keyboard.
Provides pure ctypes interface to IOKit / IOHIDManager with hardware burst sequence.
"""
import sys
import time
import logging
import threading
import ctypes
from ctypes import (
    c_void_p, c_char_p, c_uint32, c_int, c_long, c_size_t,
    byref, create_string_buffer, POINTER
)
from typing import Optional, Dict, Any, Tuple, Union, List

from .protocol import (
    VID, PID, LIGHTING_USAGE, LIGHTING_USAGE_PAGE,
    MODES, MODE_BY_NAME, encode_effect_burst
)

logger = logging.getLogger("RampageRGB.Driver")

# Load macOS frameworks
try:
    IOKit = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
    CoreFoundation = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
except Exception as e:
    logger.error(f"Failed to load macOS IOKit/CoreFoundation frameworks: {e}")
    IOKit = None
    CoreFoundation = None

# CoreFoundation & IOKit ctypes setup
kCFAllocatorDefault = None
kCFStringEncodingUTF8 = 0x08000100
kCFNumberIntType = 9
kIOHIDReportTypeFeature = 2

if CoreFoundation:
    CoreFoundation.CFStringCreateWithCString.restype = c_void_p
    CoreFoundation.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]

    CoreFoundation.CFNumberCreate.restype = c_void_p
    CoreFoundation.CFNumberCreate.argtypes = [c_void_p, c_int, c_void_p]

    CoreFoundation.CFNumberGetValue.restype = c_int
    CoreFoundation.CFNumberGetValue.argtypes = [c_void_p, c_int, c_void_p]

    CoreFoundation.CFRelease.restype = None
    CoreFoundation.CFRelease.argtypes = [c_void_p]

    CoreFoundation.CFSetGetCount.restype = c_long
    CoreFoundation.CFSetGetCount.argtypes = [c_void_p]

    CoreFoundation.CFSetGetValues.restype = None
    CoreFoundation.CFSetGetValues.argtypes = [c_void_p, POINTER(c_void_p)]

if IOKit:
    IOKit.IOHIDManagerCreate.restype = c_void_p
    IOKit.IOHIDManagerCreate.argtypes = [c_void_p, c_uint32]

    IOKit.IOHIDManagerSetDeviceMatching.restype = None
    IOKit.IOHIDManagerSetDeviceMatching.argtypes = [c_void_p, c_void_p]

    IOKit.IOHIDManagerOpen.restype = c_int
    IOKit.IOHIDManagerOpen.argtypes = [c_void_p, c_uint32]

    IOKit.IOHIDManagerClose.restype = c_int
    IOKit.IOHIDManagerClose.argtypes = [c_void_p, c_uint32]

    IOKit.IOHIDManagerCopyDevices.restype = c_void_p
    IOKit.IOHIDManagerCopyDevices.argtypes = [c_void_p]

    IOKit.IOHIDDeviceGetProperty.restype = c_void_p
    IOKit.IOHIDDeviceGetProperty.argtypes = [c_void_p, c_void_p]

    IOKit.IOHIDDeviceOpen.restype = c_int
    IOKit.IOHIDDeviceOpen.argtypes = [c_void_p, c_uint32]

    IOKit.IOHIDDeviceClose.restype = c_int
    IOKit.IOHIDDeviceClose.argtypes = [c_void_p, c_uint32]

    IOKit.IOHIDDeviceSetReport.restype = c_int
    IOKit.IOHIDDeviceSetReport.argtypes = [c_void_p, c_int, c_size_t, c_char_p, c_size_t]


def _cfstr(s: str) -> c_void_p:
    return CoreFoundation.CFStringCreateWithCString(kCFAllocatorDefault, s.encode('utf-8'), kCFStringEncodingUTF8)


def _get_int_property(dev: c_void_p, prop_name: str) -> Optional[int]:
    if not CoreFoundation or not IOKit or not dev:
        return None
    k = _cfstr(prop_name)
    prop = IOKit.IOHIDDeviceGetProperty(dev, k)
    CoreFoundation.CFRelease(k)
    if not prop:
        return None
    val = c_int(0)
    if CoreFoundation.CFNumberGetValue(prop, kCFNumberIntType, byref(val)):
        return val.value
    return None


class RampageKeyboardDriver:
    """
    Hardware Controller for Rampage SinoWealth (258A:0016) Keyboard on macOS.
    """

    def __init__(self, auto_connect: bool = True):
        self._lock = threading.Lock()
        self._manager: Optional[c_void_p] = None
        self._device: Optional[c_void_p] = None
        self._connected: bool = False
        
        self.state: Dict[str, Any] = {
            "mode": 1,
            "mode_name": "rainbow",
            "speed": 2,
            "brightness": 4,
            "last_updated": time.time()
        }

        if auto_connect:
            self.connect()

    def connect(self) -> bool:
        """Find and open the Rampage / SinoWealth lighting interface."""
        with self._lock:
            if not IOKit or not CoreFoundation:
                logger.error("IOKit / CoreFoundation libraries not available.")
                self._connected = False
                return False

            self._close_internal()

            self._manager = IOKit.IOHIDManagerCreate(kCFAllocatorDefault, 0)
            if not self._manager:
                return False

            IOKit.IOHIDManagerSetDeviceMatching(self._manager, None)
            IOKit.IOHIDManagerOpen(self._manager, 0)

            dev_set = IOKit.IOHIDManagerCopyDevices(self._manager)
            if not dev_set:
                return False

            count = CoreFoundation.CFSetGetCount(dev_set)
            devices = (c_void_p * count)()
            CoreFoundation.CFSetGetValues(dev_set, devices)

            target_dev = None
            for dev in devices:
                vid = _get_int_property(dev, "VendorID")
                pid = _get_int_property(dev, "ProductID")
                usage = _get_int_property(dev, "PrimaryUsage")

                if vid == VID and pid == PID and usage == LIGHTING_USAGE:
                    target_dev = dev
                    break

            CoreFoundation.CFRelease(dev_set)

            if not target_dev:
                self._device = None
                self._connected = False
                return False

            open_res = IOKit.IOHIDDeviceOpen(target_dev, 0)
            if open_res != 0:
                self._device = None
                self._connected = False
                return False

            self._device = target_dev
            self._connected = True
            logger.info("Connected to Rampage Keyboard Lighting Interface.")
            return True

    def _close_internal(self):
        """Close device without locking."""
        if self._device:
            try:
                IOKit.IOHIDDeviceClose(self._device, 0)
            except Exception:
                pass
            self._device = None
        if self._manager:
            try:
                IOKit.IOHIDManagerClose(self._manager, 0)
                CoreFoundation.CFRelease(self._manager)
            except Exception:
                pass
            self._manager = None
        self._connected = False

    def close(self):
        """Safely close device handles."""
        with self._lock:
            self._close_internal()

    def is_connected(self) -> bool:
        """Check if keyboard is currently connected and responsive."""
        with self._lock:
            return self._connected and self._device is not None

    def _send_frames_burst(self, frames: List[bytes], repeat_count: int = 2) -> bool:
        """Send complete 5-frame burst to the keyboard."""
        if not self._device or not self._connected:
            if not self.connect():
                return False

        all_ok = True
        for repeat in range(repeat_count):
            for frame in frames:
                report_id = frame[0]
                c_buf = create_string_buffer(frame)
                ret = IOKit.IOHIDDeviceSetReport(self._device, kIOHIDReportTypeFeature, report_id, c_buf, len(frame))
                if ret != 0:
                    all_ok = False
                time.sleep(0.005)

        return all_ok

    def set_effect(
        self,
        mode: Union[int, str],
        speed: int = 2,
        brightness: int = 4
    ) -> bool:
        """
        Apply an effect mode to the hardware keyboard.
        - mode: 1 ('rainbow'), 2 ('static'), 3 ('snake'), 0 ('off')
        - speed: 0..4
        - brightness: 0..4
        """
        with self._lock:
            if isinstance(mode, str):
                mode_id = MODE_BY_NAME.get(mode.lower(), 1)
            else:
                mode_id = int(mode)

            frames = encode_effect_burst(mode=mode_id, speed=speed, brightness=brightness)
            success = self._send_frames_burst(frames, repeat_count=2)

            if success:
                mode_info = MODES.get(mode_id, MODES[1])
                self.state.update({
                    "mode": mode_id,
                    "mode_name": mode_info["name"],
                    "speed": speed,
                    "brightness": brightness,
                    "last_updated": time.time()
                })
            return success

    def set_mode(self, mode: Union[int, str], speed: int = 2, brightness: int = 4, extra: int = 0) -> bool:
        """Alias for set_effect."""
        return self.set_effect(mode=mode, speed=speed, brightness=brightness)

    def set_static_color(self, color: str = "red", brightness: int = 4) -> bool:
        """Set keyboard to solid red static mode."""
        return self.set_effect(mode="static", speed=0, brightness=brightness)

    def turn_off(self) -> bool:
        """Turn off keyboard backlighting."""
        return self.set_effect(mode="off", speed=0, brightness=0)

    def get_status(self) -> Dict[str, Any]:
        """Return driver connection status and current lighting state."""
        connected = self.is_connected()
        if not connected:
            connected = self.connect()

        mode_info = MODES.get(self.state["mode"], MODES[1])

        return {
            "connected": connected,
            "device": {
                "name": "Rampage SinoWealth Mechanical Keyboard",
                "vendor_id": f"0x{VID:04x}",
                "product_id": f"0x{PID:04x}",
                "interface": "Lighting Control (Usage 128 / Report 5 & 6)",
                "platform": sys.platform
            },
            "state": {
                **self.state,
                "mode_title": mode_info["title"]
            }
        }


# Global driver singleton instance
_driver_instance: Optional[RampageKeyboardDriver] = None
_instance_lock = threading.Lock()

def get_driver() -> RampageKeyboardDriver:
    global _driver_instance
    with _instance_lock:
        if _driver_instance is None:
            _driver_instance = RampageKeyboardDriver(auto_connect=True)
        return _driver_instance

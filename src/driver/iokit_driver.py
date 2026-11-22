"""
macOS IOKit HID driver for the Rampage / SinoWealth (258A:0016) keyboard.

Pure ctypes bindings to IOKit + CoreFoundation (no third party packages).

The driver works read-modify-write: it reads the keyboard's own config and
colour pages, changes only the bytes for the requested setting and writes
them back, then reads again to verify. If the firmware does not answer reads
it falls back to the captured vendor templates.
"""
import sys
import json
import time
from pathlib import Path
import logging
import threading
import ctypes
from ctypes import (
    c_void_p, c_char_p, c_uint32, c_int, c_long,
    byref, create_string_buffer, POINTER,
)
from typing import Optional, Dict, Any, Union, List

from . import protocol as P

logger = logging.getLogger("RampageRGB.Driver")

try:
    IOKit = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/IOKit.framework/IOKit")
    CoreFoundation = ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    )
except Exception as e:  # pragma: no cover - non-macOS
    logger.error(f"IOKit/CoreFoundation yüklenemedi: {e}")
    IOKit = None
    CoreFoundation = None

kCFStringEncodingUTF8 = 0x08000100
kCFNumberSInt32Type = 3
kIOHIDReportTypeFeature = 2
kIOHIDOptionsTypeNone = 0

kIOReturnSuccess = 0
kIOReturnNotPermitted = 0xE00002E2
kIOReturnExclusiveAccess = 0xE00002C5
kIOReturnNoDevice = 0xE00002C0
kIOReturnNotOpen = 0xE00002CD

if CoreFoundation:
    CoreFoundation.CFStringCreateWithCString.restype = c_void_p
    CoreFoundation.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
    CoreFoundation.CFNumberGetValue.restype = ctypes.c_bool
    CoreFoundation.CFNumberGetValue.argtypes = [c_void_p, c_int, c_void_p]
    CoreFoundation.CFGetTypeID.restype = c_long
    CoreFoundation.CFGetTypeID.argtypes = [c_void_p]
    CoreFoundation.CFNumberGetTypeID.restype = c_long
    CoreFoundation.CFNumberGetTypeID.argtypes = []
    CoreFoundation.CFRelease.restype = None
    CoreFoundation.CFRelease.argtypes = [c_void_p]
    CoreFoundation.CFRetain.restype = c_void_p
    CoreFoundation.CFRetain.argtypes = [c_void_p]
    CoreFoundation.CFSetGetCount.restype = c_long
    CoreFoundation.CFSetGetCount.argtypes = [c_void_p]
    CoreFoundation.CFSetGetValues.restype = None
    CoreFoundation.CFSetGetValues.argtypes = [c_void_p, POINTER(c_void_p)]

if IOKit:
    IOKit.IOHIDManagerCreate.restype = c_void_p
    IOKit.IOHIDManagerCreate.argtypes = [c_void_p, c_uint32]
    IOKit.IOHIDManagerSetDeviceMatching.restype = None
    IOKit.IOHIDManagerSetDeviceMatching.argtypes = [c_void_p, c_void_p]
    IOKit.IOHIDManagerCopyDevices.restype = c_void_p
    IOKit.IOHIDManagerCopyDevices.argtypes = [c_void_p]
    IOKit.IOHIDDeviceGetProperty.restype = c_void_p
    IOKit.IOHIDDeviceGetProperty.argtypes = [c_void_p, c_void_p]
    IOKit.IOHIDDeviceOpen.restype = c_int
    IOKit.IOHIDDeviceOpen.argtypes = [c_void_p, c_uint32]
    IOKit.IOHIDDeviceClose.restype = c_int
    IOKit.IOHIDDeviceClose.argtypes = [c_void_p, c_uint32]
    IOKit.IOHIDDeviceSetReport.restype = c_int
    IOKit.IOHIDDeviceSetReport.argtypes = [c_void_p, c_int, c_long, c_char_p, c_long]
    IOKit.IOHIDDeviceGetReport.restype = c_int
    IOKit.IOHIDDeviceGetReport.argtypes = [c_void_p, c_int, c_long, c_char_p, POINTER(c_long)]


def _u32(code: int) -> int:
    return code & 0xFFFFFFFF


def _cfstr(s: str) -> c_void_p:
    return CoreFoundation.CFStringCreateWithCString(None, s.encode("utf-8"), kCFStringEncodingUTF8)


def _get_int_property(dev: int, prop_name: str) -> Optional[int]:
    key = _cfstr(prop_name)
    try:
        prop = IOKit.IOHIDDeviceGetProperty(dev, key)
    finally:
        CoreFoundation.CFRelease(key)
    if not prop or CoreFoundation.CFGetTypeID(prop) != CoreFoundation.CFNumberGetTypeID():
        return None
    val = ctypes.c_int32(0)
    if CoreFoundation.CFNumberGetValue(prop, kCFNumberSInt32Type, byref(val)):
        return val.value
    return None


SETTINGS_FILE = Path.home() / ".rampage_rgb_settings.json"

PERMISSION_HELP = (
    "macOS bu uygulamanın klavyeye erişmesine izin vermiyor. "
    "Sistem Ayarları → Gizlilik ve Güvenlik → Giriş İzleme (Input Monitoring) "
    "bölümünde uygulamayı başlattığınız Terminal'i (veya Python'u) açın, "
    "sonra uygulamayı yeniden başlatın."
)


class DeviceError(Exception):
    pass


class RampageKeyboardDriver:
    """Hardware controller for the Rampage SinoWealth (258A:0016) keyboard."""

    STATUS_RETRY_SECONDS = 2.0

    def __init__(self, auto_connect: bool = True):
        self._lock = threading.RLock()
        self._manager: Optional[int] = None
        self._device: Optional[int] = None
        self._connected = False
        self._found = False
        self._last_attempt = 0.0
        self.error: Optional[str] = None
        self.error_code: Optional[str] = None

        # Pages mirroring the keyboard state. ``_synced`` is True when they
        # were read back from the hardware (not just assumed from templates).
        self._config = P.default_config_page()
        self._colors = P.default_colors_page()
        self._synced = False
        self.readback_supported: Optional[bool] = None
        self.last_verified: Optional[bool] = None
        self.last_on_mode = 9
        self.last_updated = time.time()
        self.variant: Optional[str] = None
        self.variant_confirmed = False
        self._initialized: set = set()
        self._load_settings()

        if auto_connect:
            self.connect()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        with self._lock:
            self._last_attempt = time.time()
            if not IOKit or not CoreFoundation:
                self._set_error("unsupported", "Bu uygulama yalnızca macOS üzerinde çalışır.")
                return False

            self._close_internal()
            self._manager = IOKit.IOHIDManagerCreate(None, 0)
            if not self._manager:
                self._set_error("iokit", "IOHIDManager oluşturulamadı.")
                return False
            IOKit.IOHIDManagerSetDeviceMatching(self._manager, None)

            dev_set = IOKit.IOHIDManagerCopyDevices(self._manager)
            target = None
            if dev_set:
                count = CoreFoundation.CFSetGetCount(dev_set)
                devices = (c_void_p * count)()
                CoreFoundation.CFSetGetValues(dev_set, devices)
                for dev in devices:
                    if (
                        _get_int_property(dev, "VendorID") == P.VID
                        and _get_int_property(dev, "ProductID") == P.PID
                        and _get_int_property(dev, "PrimaryUsage") == P.LIGHTING_USAGE
                    ):
                        target = CoreFoundation.CFRetain(dev)
                        break
                CoreFoundation.CFRelease(dev_set)

            self._found = target is not None
            if not target:
                self._set_error("not_found", "Rampage klavye (258A:0016) bulunamadı. USB kablosunu kontrol edin.")
                return False

            res = _u32(IOKit.IOHIDDeviceOpen(target, kIOHIDOptionsTypeNone))
            if res != kIOReturnSuccess:
                CoreFoundation.CFRelease(target)
                if res == kIOReturnNotPermitted:
                    self._set_error("permission", PERMISSION_HELP)
                elif res == kIOReturnExclusiveAccess:
                    self._set_error("busy", "Klavye başka bir uygulama tarafından kullanılıyor (ör. üretici yazılımı). Onu kapatıp tekrar deneyin.")
                else:
                    self._set_error("open_failed", f"Klavye açılamadı (IOKit 0x{res:08X}).")
                return False

            self._device = target
            self._connected = True
            self.error = None
            self.error_code = None
            logger.info("Rampage aydınlatma arayüzüne bağlanıldı.")
            self.readback_supported = None  # probe again on every (re)connect
            self._initialized.clear()
            self._sync_from_device()
            return True

    def _set_error(self, code: str, message: str):
        self.error_code = code
        self.error = message
        self._connected = False
        logger.info(message)

    def _close_internal(self):
        if self._device:
            try:
                IOKit.IOHIDDeviceClose(self._device, kIOHIDOptionsTypeNone)
                CoreFoundation.CFRelease(self._device)
            except Exception:
                pass
            self._device = None
        if self._manager:
            try:
                CoreFoundation.CFRelease(self._manager)
            except Exception:
                pass
            self._manager = None
        self._connected = False

    def close(self):
        with self._lock:
            self._close_internal()

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected and self._device is not None

    def _ensure_connected(self):
        if not self.is_connected() and not self.connect():
            raise DeviceError(self.error or "Klavye bağlı değil.")

    # ------------------------------------------------------------------
    # Low-level reports
    # ------------------------------------------------------------------
    def _set_report(self, data: bytes) -> int:
        buf = create_string_buffer(bytes(data), len(data))
        return _u32(IOKit.IOHIDDeviceSetReport(
            self._device, kIOHIDReportTypeFeature, data[0], buf, len(data)
        ))

    def _get_report(self, report_id: int, length: int) -> Optional[bytes]:
        buf = create_string_buffer(bytes([report_id]) + bytes(length - 1), length)
        size = c_long(length)
        res = _u32(IOKit.IOHIDDeviceGetReport(
            self._device, kIOHIDReportTypeFeature, report_id, buf, byref(size)
        ))
        if res != kIOReturnSuccess or size.value <= 0:
            return None
        raw = buf.raw[: size.value]
        if raw[0] != report_id:
            # Some stacks strip the report id; re-add it so offsets stay aligned.
            raw = bytes([report_id]) + raw
        return raw

    def _write(self, data: bytes):
        res = self._set_report(data)
        if res == kIOReturnSuccess:
            return
        if res in (kIOReturnNoDevice, kIOReturnNotOpen):
            self._close_internal()
            self._set_error("not_found", "Klavye bağlantısı koptu.")
        raise DeviceError(f"Klavyeye yazılamadı (IOKit 0x{res:08X}).")

    def _read_page(self, page) -> Optional[bytearray]:
        if self.readback_supported is False:
            return None
        if self._set_report(P.read_request(page)) != kIOReturnSuccess:
            return None
        time.sleep(0.01)
        raw = self._get_report(P.REPORT_ID_DATA, P.PAYLOAD_LEN)
        if raw is None:
            return None
        base = self._config if page[0] == P.PAGE_CONFIG[0] else self._colors
        return P.normalize_read(page, raw, base)

    def _pages(self, variant: Optional[str] = None):
        v = P.VARIANTS[variant or self.variant or P.DEFAULT_VARIANT]
        return v["config"], v["colors"]

    def _read_config(self, variant: Optional[str] = None) -> Optional[bytearray]:
        page = self._read_page(self._pages(variant)[0])
        return page if P.is_valid_config(page) else None

    def _read_colors(self, variant: Optional[str] = None) -> Optional[bytearray]:
        page = self._read_page(self._pages(variant)[1])
        return page if P.is_valid_colors(page) else None

    def _sync_from_device(self) -> bool:
        config = self._read_config()
        if config is None:
            if self.readback_supported is None:
                self.readback_supported = False
                logger.info("Klavye okuma desteklemiyor; doğrulama yapılamayacak.")
            return False
        self.readback_supported = True
        self._config = config
        colors = self._read_colors()
        if colors is not None:
            self._colors = colors
        self._synced = True
        if config[P.IDX_MODE] in P.MODES and config[P.IDX_MODE] and not P.is_custom(config):
            self.last_on_mode = config[P.IDX_MODE]
        self.last_updated = time.time()
        return True

    # ------------------------------------------------------------------
    # Protocol variant
    # ------------------------------------------------------------------
    def _load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        v = data.get("protocol")
        self.variant = v if v in P.VARIANTS else None
        self.variant_confirmed = bool(data.get("protocol_confirmed")) and self.variant is not None

    def _save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps({
                "protocol": self.variant,
                "protocol_confirmed": self.variant_confirmed,
            }), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Ayarlar kaydedilemedi: {e}")

    def set_variant(self, variant: Optional[str]):
        """Force a protocol variant (None = detect automatically)."""
        with self._lock:
            if variant is not None and variant not in P.VARIANTS:
                raise ValueError(f"Bilinmeyen protokol: {variant}")
            self.variant = variant
            self.variant_confirmed = False
            self._initialized.clear()
            self._save_settings()

    def _candidates(self) -> List[str]:
        if self.variant and (self.variant_confirmed or not self.readback_supported):
            return [self.variant]
        first = self.variant or P.DEFAULT_VARIANT
        return [first] + [v for v in P.VARIANTS if v != first]

    def _is_applied(self, readback: Optional[bytes], config: bytes, mode_id: int) -> bool:
        if readback is None:
            return False
        if mode_id == P.MODE_CUSTOM:
            return P.is_custom(readback) and readback[P.IDX_CUSTOM] == config[P.IDX_CUSTOM]
        if readback[P.IDX_MODE] != mode_id or readback[P.IDX_PER_KEY]:
            return False
        if mode_id == 0:
            return True
        ci = P.MODE_SLOT_BASE + 2 * mode_id
        return readback[ci:ci + 2] == config[ci:ci + 2]

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------
    def apply(
        self,
        mode: Union[int, str],
        speed: Optional[int] = None,
        brightness: Optional[int] = None,
        color: Optional[int] = None,
        direction_left: Optional[bool] = None,
        palette: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """Apply a lighting mode. Settings left as ``None`` keep their stored value.

        ``palette`` is ``{preset_index: '#RRGGBB'}`` for the mode's 7 colour slots.
        Returns ``{"success", "verified", "error"}``; ``verified`` is None when
        the keyboard cannot be read back.
        """
        mode_id = P.resolve_mode(mode)

        def build():
            config = P.build_config_page(self._config, mode_id, speed, brightness, color, direction_left)
            colors = P.build_colors_page(self._colors, mode_id, palette) if palette and mode_id else None
            return config, colors

        return self._run(mode_id, build)

    def apply_custom(self, profile: int) -> Dict[str, Any]:
        """Switch to the per-key custom profile stored on the keyboard (1..5)."""
        index = int(profile) - 1
        P.build_custom_page(self._config, index)  # validates the range
        return self._run(P.MODE_CUSTOM, lambda: (P.build_custom_page(self._config, index), None))

    def _run(self, mode_id, build) -> Dict[str, Any]:
        with self._lock:
            try:
                self._ensure_connected()
                # Refresh from hardware so we never overwrite settings changed with Fn keys.
                self._sync_from_device()
                config, colors = build()
                result = self._send(mode_id, config, colors)
            except DeviceError as e:
                result = {"success": False, "verified": False, "error": str(e)}
            self.last_verified = result["verified"]
            return result

    def _send(self, mode_id, config, colors):
        for variant in self._candidates():
            cfg_page, col_page = self._pages(variant)
            init = P.VARIANTS[variant]["init"]
            if init and variant not in self._initialized:
                self._set_report(init)
                time.sleep(0.02)
                self._initialized.add(variant)

            if colors is not None:
                colors[0:6] = bytes([P.REPORT_ID_DATA, col_page[0], col_page[1], 0, col_page[2], 0])
                self._write(colors)
                time.sleep(0.01)
            config[0:6] = bytes([P.REPORT_ID_DATA, cfg_page[0], cfg_page[1], 0, cfg_page[2], 0])
            self._write(config)

            if not self.readback_supported:
                self.variant = variant
                self._commit(mode_id, config, colors)
                return {"success": True, "verified": None, "error": None, "protocol": variant}

            time.sleep(0.05)
            readback = self._read_config(variant)
            if self._is_applied(readback, config, mode_id):
                if self.variant != variant or not self.variant_confirmed:
                    logger.info(f"Çalışan protokol bulundu: {variant}")
                    self.variant, self.variant_confirmed = variant, True
                    self._save_settings()
                self._commit(mode_id, readback, colors)
                return {"success": True, "verified": True, "error": None, "protocol": variant}
            logger.warning(f"Protokol '{variant}' ile yazılan ayar klavyede görünmüyor.")

        return {
            "success": False,
            "verified": False,
            "error": "Klavye komutu kabul etmedi (geri okumada değişiklik yok).",
        }

    def _commit(self, mode_id, config, colors):
        self._config = bytearray(config)
        if colors is not None:
            self._colors = bytearray(colors)
        if mode_id in P.MODES and mode_id:
            self.last_on_mode = mode_id
        self.last_updated = time.time()

    def set_effect(self, mode: Union[int, str], speed: int = 2, brightness: int = 4) -> bool:
        """Backward compatible helper."""
        return self.apply(mode, speed=speed, brightness=brightness)["success"]

    def set_static_color(self, color: str = "#FF0000", brightness: Optional[int] = None) -> Dict[str, Any]:
        """Solid colour on every key (any RGB value)."""
        return self.apply("static", brightness=brightness, color=0, palette={0: color})

    def turn_off(self) -> Dict[str, Any]:
        return self.apply(0)

    def turn_on(self) -> Dict[str, Any]:
        return self.apply(self.last_on_mode or 9)

    def refresh(self) -> bool:
        with self._lock:
            if not self.is_connected():
                return self.connect()
            return self._sync_from_device()

    def get_status(self, refresh: bool = True) -> Dict[str, Any]:
        with self._lock:
            if not self.is_connected():
                if time.time() - self._last_attempt >= self.STATUS_RETRY_SECONDS:
                    self.connect()
            elif refresh and self.readback_supported:
                if not self._sync_from_device():
                    # A read that used to work now fails: most likely unplugged.
                    self._close_internal()
                    self.connect()

            state = P.describe_state(self._config, self._colors)
            return {
                "connected": self.is_connected(),
                "found": self._found,
                "error": self.error,
                "error_code": self.error_code,
                "device": {
                    "name": "Rampage (SinoWealth) Mekanik Klavye",
                    "vendor_id": f"0x{P.VID:04x}",
                    "product_id": f"0x{P.PID:04x}",
                    "platform": sys.platform,
                },
                "readback": bool(self.readback_supported),
                "synced": self._synced,
                "last_verified": self.last_verified,
                "protocol": self.variant,
                "protocol_confirmed": self.variant_confirmed,
                "last_on_mode": self.last_on_mode,
                "state": {**state, "last_updated": self.last_updated},
            }


_driver_instance: Optional[RampageKeyboardDriver] = None
_instance_lock = threading.Lock()


def get_driver() -> RampageKeyboardDriver:
    global _driver_instance
    with _instance_lock:
        if _driver_instance is None:
            _driver_instance = RampageKeyboardDriver(auto_connect=True)
        return _driver_instance

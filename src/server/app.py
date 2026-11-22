"""
HTTP server and REST API for the Rampage RGB controller.
Standard library only.
"""
import json
import time
import logging
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..driver.protocol import CUSTOM_PROFILES
from ..driver import (
    get_driver, MODES, KEYBOARD_LAYOUT, DEFAULT_PALETTE, COLOR_RANDOM, MAX_LEVEL, resolve_mode,
)

logger = logging.getLogger("RampageRGB.Server")

PROFILES_FILE = Path.home() / ".rampage_rgb_profiles.json"
UI_DIR = Path(__file__).resolve().parent.parent / "ui"

_GLOBAL_HTTPD: Optional[ThreadingHTTPServer] = None

DEFAULT_PROFILES = [
    {"id": "rainbow_wave", "name": "Gökkuşağı Dalgası", "mode": "rainbow",
     "brightness": 4, "speed": 2, "color": COLOR_RANDOM, "direction_left": False, "is_default": True},
    {"id": "red_dragon", "name": "Kızıl Ejderha", "mode": "static",
     "brightness": 4, "speed": 0, "color": 0, "palette": {"0": "#FF0000"}, "is_default": True},
    {"id": "retro_snake", "name": "Retro Yılan", "mode": "snake",
     "brightness": 4, "speed": 3, "color": COLOR_RANDOM, "is_default": True},
    {"id": "calm_breath", "name": "Sakin Nefes", "mode": "breathing",
     "brightness": 3, "speed": 1, "color": 0, "palette": {"0": "#00B4FF"}, "is_default": True},
]


def load_profiles() -> List[Dict[str, Any]]:
    if not PROFILES_FILE.exists():
        save_profiles(DEFAULT_PROFILES)
        return list(DEFAULT_PROFILES)
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else list(DEFAULT_PROFILES)
    except Exception as e:
        logger.error(f"Profiller okunamadı: {e}")
        return list(DEFAULT_PROFILES)


def save_profiles(profiles: List[Dict[str, Any]]) -> bool:
    try:
        tmp = PROFILES_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        tmp.replace(PROFILES_FILE)
        return True
    except Exception as e:
        logger.error(f"Profiller kaydedilemedi: {e}")
        return False


def _opt_level(body: Dict[str, Any], key: str) -> Optional[int]:
    if body.get(key) is None:
        return None
    v = int(body[key])
    if not 0 <= v <= MAX_LEVEL:
        raise ValueError(f"{key} 0-{MAX_LEVEL} arasında olmalı")
    return v


def _palette_arg(value: Any) -> Optional[Dict[int, str]]:
    if not value:
        return None
    if isinstance(value, list):
        return {i: c for i, c in enumerate(value) if c}
    if isinstance(value, dict):
        return {int(k): v for k, v in value.items() if v}
    raise ValueError("palette liste veya sözlük olmalı")


NAMED_COLORS = {
    "red": "#FF0000", "kırmızı": "#FF0000", "green": "#00FF00", "yeşil": "#00FF00",
    "blue": "#0000FF", "mavi": "#0000FF", "white": "#FFFFFF", "beyaz": "#FFFFFF",
    "cyan": "#00FFFF", "yellow": "#FFFF00", "sarı": "#FFFF00",
    "magenta": "#FF00FF", "purple": "#A020F0", "mor": "#A020F0", "orange": "#FF8000", "turuncu": "#FF8000",
}


def _color_arg(color: Any, palette: Any):
    """Accept a preset index (0-7), 'random'/'rainbow', a colour name or '#RRGGBB'."""
    palette = _palette_arg(palette)
    if color is None or isinstance(color, bool):
        return None, palette
    if isinstance(color, (int, float)) or str(color).isdigit():
        value = int(color)
        if not 0 <= value <= COLOR_RANDOM:
            raise ValueError("color 0-7 arasında olmalı")
        return value, palette
    text = str(color).strip().lower()
    if text in ("random", "rainbow", "rastgele", "renkli"):
        return COLOR_RANDOM, palette
    hex_value = NAMED_COLORS.get(text, text if text.startswith("#") else None)
    if not hex_value:
        raise ValueError(f"Bilinmeyen renk: {color}")
    return 0, {**(palette or {}), 0: hex_value}


def _mode_title(profile: Dict[str, Any]) -> str:
    mode = str(profile.get("mode", "")).lower()
    if mode in ("custom", "custom_preset"):
        return f"Özel tuş profili {profile.get('profile') or profile.get('custom_preset') or 1}"
    try:
        return MODES[resolve_mode(mode)]["title"]
    except ValueError:
        return mode


def apply_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a settings body and send it to the keyboard."""
    if str(body.get("mode", "")).lower() in ("custom", "custom_preset"):
        return get_driver().apply_custom(int(body.get("profile") or body.get("custom_preset") or 1))
    mode_id = resolve_mode(body.get("mode"))
    color, palette = _color_arg(body.get("color"), body.get("palette"))
    direction = body.get("direction_left")
    return get_driver().apply(
        mode_id,
        speed=_opt_level(body, "speed"),
        brightness=_opt_level(body, "brightness"),
        color=color,
        direction_left=None if direction is None else bool(direction),
        palette=palette,
    )


class RampageAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, data: Any, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _result(self, result: Dict[str, Any]):
        drv = get_driver()
        status = drv.get_status(refresh=False)
        self._send_json({**result, "status": status}, 200 if result.get("success") else 503)

    # ------------------------------------------------------------------
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/device/status":
            self._send_json(get_driver().get_status())
        elif path == "/api/device/modes":
            self._send_json({
                "modes": list(MODES.values()),
                "default_palette": DEFAULT_PALETTE,
                "color_random": COLOR_RANDOM,
                "max_level": MAX_LEVEL,
                "custom_profiles": CUSTOM_PROFILES,
            })
        elif path == "/api/device/layout":
            self._send_json({"rows": KEYBOARD_LAYOUT})
        elif path == "/api/profiles":
            self._send_json([{**p, "mode_title": _mode_title(p)} for p in load_profiles()])
        else:
            super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        body = self._read_json_body()
        if body is None:
            self._send_json({"success": False, "error": "Geçersiz JSON"}, 400)
            return

        drv = get_driver()
        try:
            if path in ("/api/device/apply", "/api/device/mode"):
                self._result(apply_settings(body))
            elif path == "/api/device/static-color":
                self._result(drv.set_static_color(body.get("color", "#FF0000"), _opt_level(body, "brightness")))
            elif path == "/api/device/off":
                self._result(drv.turn_off())
            elif path == "/api/device/on":
                self._result(drv.turn_on())
            elif path == "/api/device/custom":
                self._result(drv.apply_custom(int(body.get("profile", 1))))
            elif path == "/api/device/reconnect":
                ok = drv.connect()
                self._result({"success": ok, "error": None if ok else drv.error})
            elif path == "/api/profiles":
                self._save_profile(body)
            elif path == "/api/profiles/apply":
                target = next((p for p in load_profiles() if p.get("id") == body.get("id")), None)
                if not target:
                    self._send_json({"success": False, "error": "Profil bulunamadı"}, 404)
                else:
                    self._result(apply_settings(target))
            elif path == "/api/server/shutdown":
                self._send_json({"success": True})
                threading.Thread(target=_shutdown_soon, daemon=True).start()
            else:
                self._send_json({"success": False, "error": "Bulunamadı"}, 404)
        except ValueError as e:
            self._send_json({"success": False, "error": str(e)}, 400)
        except Exception as e:  # keep the server alive no matter what
            logger.exception("İstek işlenemedi")
            self._send_json({"success": False, "error": f"Beklenmeyen hata: {e}"}, 500)

    def _save_profile(self, body: Dict[str, Any]):
        name = str(body.get("name", "")).strip()
        if not name:
            raise ValueError("Profil adı boş olamaz")
        mode_id = resolve_mode(body.get("mode"))
        profile = {
            "id": body.get("id") or f"profile_{int(time.time() * 1000)}",
            "name": name[:40],
            "mode": MODES[mode_id]["name"],
            "brightness": _opt_level(body, "brightness"),
            "speed": _opt_level(body, "speed"),
            "color": body.get("color"),
            "direction_left": bool(body.get("direction_left", False)),
            "palette": body.get("palette"),
            "is_default": False,
        }
        profiles = load_profiles()
        for i, p in enumerate(profiles):
            if p.get("id") == profile["id"]:
                profiles[i] = profile
                break
        else:
            profiles.append(profile)
        save_profiles(profiles)
        self._send_json({"success": True, "profile": profile, "profiles": profiles})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/profiles":
            self._send_json({"success": False, "error": "Bulunamadı"}, 404)
            return
        profile_id = urllib.parse.parse_qs(parsed.query).get("id", [None])[0]
        profiles = load_profiles()
        filtered = [p for p in profiles if p.get("id") != profile_id]
        if len(filtered) == len(profiles):
            self._send_json({"success": False, "error": "Profil bulunamadı"}, 404)
            return
        save_profiles(filtered)
        self._send_json({"success": True, "profiles": filtered})

    def log_message(self, format, *args):
        pass


def _shutdown_soon():
    time.sleep(0.2)
    if _GLOBAL_HTTPD:
        _GLOBAL_HTTPD.shutdown()


def run_server(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False):
    global _GLOBAL_HTTPD
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        httpd = ThreadingHTTPServer((host, port), RampageAPIHandler)
    except OSError:
        url = f"http://{host}:{port}"
        print(f"Port {port} kullanımda; uygulama zaten açık olabilir: {url}")
        if open_browser:
            import webbrowser
            webbrowser.open(url)
        return
    _GLOBAL_HTTPD = httpd

    url = f"http://{host}:{port}"
    print(f"🚀 Rampage RGB arayüzü: {url}")
    print("Durdurmak için arayüzdeki 'Kapat' düğmesini veya Ctrl+C'yi kullanın.")
    get_driver()  # connect early so the first page load is fast

    if open_browser:
        import webbrowser
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        httpd.server_close()
        get_driver().close()
        print("\nSunucu kapatıldı. Klavyenin ışık ayarları klavyede kayıtlı kalır.")


if __name__ == "__main__":
    run_server()

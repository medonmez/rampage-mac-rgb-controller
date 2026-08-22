"""
HTTP Server and REST API for Rampage RGB Controller.
Pure standard library implementation (Zero external dependencies).
"""
import os
import sys
import json
import time
import signal
import socket
import logging
import threading
import urllib.parse
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..driver import (
    get_driver, MODES,
    KEYBOARD_LAYOUT, KEY_GROUPS
)

logger = logging.getLogger("RampageRGB.Server")

PROFILES_FILE = Path.home() / ".rampage_rgb_profiles.json"
UI_DIR = Path(__file__).resolve().parent.parent / "ui"

_GLOBAL_HTTPD: Optional[ThreadingHTTPServer] = None

DEFAULT_PROFILES = [
    {
        "id": "rainbow_wave",
        "name": "Gökkuşağı Dalgası",
        "description": "Canlı ve akıcı tam spektrum gökkuşağı animasyonu",
        "mode": "rainbow",
        "brightness": 4,
        "speed": 3,
        "color": "#FF0055",
        "is_default": True
    },
    {
        "id": "red_dragon",
        "name": "Sabit Kırmızı (Kızıl Ejderha)",
        "description": "Statik parlak kırmızı gamer aydınlatması",
        "mode": "static",
        "color": "#FF0000",
        "brightness": 4,
        "speed": 0,
        "is_default": True
    },
    {
        "id": "retro_snake",
        "name": "Retro Yılan",
        "description": "Nostaljik yılan oyunu animasyonu",
        "mode": "snake",
        "brightness": 4,
        "speed": 3,
        "color": "#00FF00",
        "is_default": True
    }
]


def load_profiles() -> List[Dict[str, Any]]:
    """Load user profiles from file or create defaults."""
    if not PROFILES_FILE.exists():
        save_profiles(DEFAULT_PROFILES)
        return DEFAULT_PROFILES
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            profiles = json.load(f)
            return profiles
    except Exception as e:
        logger.error(f"Error loading profiles: {e}")
        return DEFAULT_PROFILES


def save_profiles(profiles: List[Dict[str, Any]]) -> bool:
    """Save profiles to JSON file."""
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving profiles: {e}")
        return False


class RampageAPIHandler(SimpleHTTPRequestHandler):
    """Handles REST API requests and serves the Web UI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def _set_json_headers(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_json_headers(200)

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            body_bytes = self.rfile.read(content_length)
            return json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Error parsing JSON request: {e}")
            return None

    def _send_json(self, data: Any, status: int = 200):
        self._set_json_headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/device/status":
            drv = get_driver()
            status = drv.get_status()
            self._send_json(status)
            return

        if path == "/api/device/modes":
            self._send_json(list(MODES.values()))
            return

        if path == "/api/device/layout":
            self._send_json({
                "rows": KEYBOARD_LAYOUT,
                "groups": KEY_GROUPS
            })
            return

        if path == "/api/profiles":
            profiles = load_profiles()
            self._send_json(profiles)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        if body is None:
            self._send_json({"error": "Invalid JSON body"}, status=400)
            return

        drv = get_driver()

        # Clean Graceful Shutdown Endpoint
        if path == "/api/server/shutdown":
            self._send_json({
                "success": True,
                "message": "Uygulama kapatıldı. Klavyeniz mevcut aydınlatma modunda kalacaktır."
            })

            def _clean_shutdown():
                time.sleep(0.2)
                global _GLOBAL_HTTPD
                if _GLOBAL_HTTPD:
                    _GLOBAL_HTTPD.shutdown()

            threading.Thread(target=_clean_shutdown, daemon=True).start()
            return

        if path == "/api/device/mode":
            mode = body.get("mode", 1)
            speed = body.get("speed", 2)
            brightness = body.get("brightness", 4)

            success = drv.set_effect(mode=mode, speed=speed, brightness=brightness)
            self._send_json({
                "success": success,
                "state": drv.get_status()["state"]
            })
            return

        if path == "/api/device/static-color":
            brightness = body.get("brightness", 4)
            success = drv.set_static_color(color="red", brightness=brightness)
            self._send_json({
                "success": success,
                "state": drv.get_status()["state"]
            })
            return

        if path == "/api/device/off":
            success = drv.turn_off()
            self._send_json({
                "success": success,
                "state": drv.get_status()["state"]
            })
            return

        if path == "/api/profiles":
            profiles = load_profiles()
            name = body.get("name", "Yeni Profil")
            profile_id = body.get("id") or f"profile_{int(time.time())}"
            new_profile = {
                "id": profile_id,
                "name": name,
                "description": body.get("description", ""),
                "mode": body.get("mode", "rainbow"),
                "brightness": body.get("brightness", 4),
                "speed": body.get("speed", 2),
                "is_default": False
            }

            updated = False
            for idx, p in enumerate(profiles):
                if p["id"] == profile_id:
                    profiles[idx] = new_profile
                    updated = True
                    break
            if not updated:
                profiles.append(new_profile)

            save_profiles(profiles)
            self._send_json({"success": True, "profile": new_profile, "profiles": profiles})
            return

        if path == "/api/profiles/apply":
            profile_id = body.get("id")
            profiles = load_profiles()
            target = next((p for p in profiles if p["id"] == profile_id), None)
            if not target:
                self._send_json({"error": "Profile not found"}, status=404)
                return

            mode = target.get("mode", "rainbow")
            brightness = target.get("brightness", 4)
            speed = target.get("speed", 2)

            success = drv.set_effect(mode=mode, speed=speed, brightness=brightness)
            self._send_json({
                "success": success,
                "applied_profile": target,
                "state": drv.get_status()["state"]
            })
            return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/profiles":
            profile_id = query.get("id", [None])[0]
            if not profile_id:
                self._send_json({"error": "Missing profile id"}, status=400)
                return

            profiles = load_profiles()
            filtered = [p for p in profiles if p["id"] != profile_id]
            if len(filtered) == len(profiles):
                self._send_json({"error": "Profile not found"}, status=404)
                return

            save_profiles(filtered)
            self._send_json({"success": True, "profiles": filtered})
            return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def log_message(self, format, *args):
        pass


def run_server(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False):
    """Start the HTTP server."""
    global _GLOBAL_HTTPD
    server_address = (host, port)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, RampageAPIHandler)
    _GLOBAL_HTTPD = httpd
    
    url = f"http://{host}:{port}"
    print(f"🚀 Rampage RGB Controller Web Sunucusu Başlatıldı: {url}")
    print("Durdurmak için arayüzdeki 'Uygulamayı Kapat' butonunu kullanabilir veya Ctrl + C yapabilirsiniz.")

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
        print("\nSunucu kapatıldı. Klavyenizin ışık ayarları korundu.")


if __name__ == "__main__":
    run_server(port=8765)

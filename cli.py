#!/usr/bin/env python3
"""
Rampage RGB (SinoWealth 258A:0016) keyboard controller CLI for macOS.
"""
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.driver import get_driver, MODES, COLOR_RANDOM, resolve_mode  # noqa: E402
from src.server.app import run_server, load_profiles, apply_settings  # noqa: E402

GREEN, RED, YELLOW, CYAN, GREY, BOLD, RESET = (
    "\033[1;32m", "\033[1;31m", "\033[1;33m", "\033[1;36m", "\033[90m", "\033[1m", "\033[0m"
)
SPEED_LABELS = ["Çok yavaş", "Yavaş", "Normal", "Hızlı", "Çok hızlı"]


def banner():
    print(f"{BOLD}RAMPAGE RGB{RESET} {GREY}• macOS • SinoWealth 258A:0016{RESET}")


def fail(msg: str, code: int = 1):
    print(f"{RED}✗ {msg}{RESET}")
    sys.exit(code)


def report(result, ok_msg: str):
    if not result.get("success"):
        fail(result.get("error") or "Komut gönderilemedi.")
    note = ""
    if result.get("verified") is True:
        note = f" {GREY}(klavyeden doğrulandı){RESET}"
    elif result.get("verified") is False:
        note = f" {YELLOW}(gönderildi, doğrulanamadı){RESET}"
    print(f"{GREEN}✓ {ok_msg}{RESET}{note}")


def cmd_status(args):
    banner()
    st = get_driver().get_status()
    if not st["connected"]:
        print(f"{RED}✗ Bağlı değil{RESET}")
        print(f"  {st.get('error') or 'Klavye bulunamadı.'}")
        sys.exit(1)
    s = st["state"]
    src = "durum klavyeden okundu" if st["readback"] else "klavye okunamıyor, son gönderilen ayar"
    print(f"{GREEN}✓ Klavye bağlı{RESET} {GREY}({src}){RESET}")
    if s.get("per_key"):
        print(f"  Mod        : {s['mode_title']} (Fn tuşlarıyla seçilmiş özel profil)")
        return
    print(f"  Mod        : #{s['mode']} {s['mode_title']}")
    if s["mode"]:
        print(f"  Parlaklık  : {s['brightness']}/4")
        print(f"  Hız        : {s['speed']}/4 ({SPEED_LABELS[s['speed']]})")
        color = "Renkli (rastgele)" if s["color"] == COLOR_RANDOM else f"Renk {s['color'] + 1}: {s['palette'][s['color']]}"
        print(f"  Renk       : {color}")
        print(f"  Yön        : {'Sola' if s['direction_left'] else 'Sağa'}")


def cmd_list_modes(args):
    banner()
    for mid, m in MODES.items():
        if not m.get("supported", True):
            continue
        feats = [n for f, n in (("has_speed", "hız"), ("has_color", "renk"), ("has_direction", "yön")) if m[f]]
        print(f"  {mid:>2}  {CYAN}{m['name']:<14}{RESET} {m['title']:<20} {GREY}{', '.join(feats)}{RESET}")


def cmd_list_profiles(args):
    banner()
    for p in load_profiles():
        tag = f" {GREY}(varsayılan){RESET}" if p.get("is_default") else ""
        print(f"  {CYAN}{p['id']}{RESET}  {p['name']}{tag}  {GREY}mod: {p.get('mode')}{RESET}")


def _color_arg(value):
    if value is None:
        return None, None
    if value.lower() in ("random", "rastgele", "renkli"):
        return COLOR_RANDOM, None
    if value.isdigit() and 1 <= int(value) <= 7:
        return int(value) - 1, None
    return 0, {"0": value}


def cmd_mode(args):
    try:
        mode_id = resolve_mode(args.mode)
    except ValueError as e:
        fail(str(e))
    color, palette = _color_arg(args.color)
    body = {"mode": mode_id, "speed": args.speed, "brightness": args.brightness, "color": color, "palette": palette}
    if args.left or args.right:
        body["direction_left"] = bool(args.left)
    report(apply_settings(body), f"Mod uygulandı: {MODES[mode_id]['title']}")


def cmd_static(args):
    report(get_driver().set_static_color(args.color, args.brightness), f"Sabit renk: {args.color}")


def cmd_profile(args):
    q = args.name.lower()
    target = next((p for p in load_profiles() if p.get("id", "").lower() == q or p.get("name", "").lower() == q), None)
    if not target:
        fail(f"'{args.name}' adında profil yok. 'list-profiles' ile bakabilirsiniz.")
    report(apply_settings(target), f"Profil uygulandı: {target['name']}")


def cmd_off(args):
    report(get_driver().turn_off(), "Işıklar kapatıldı.")


def cmd_on(args):
    drv = get_driver()
    report(drv.turn_on(), "Işıklar açıldı.")


def cmd_custom(args):
    report(get_driver().apply_custom(args.number), f"Özel tuş profili {args.number} açıldı.")


def cmd_ui(args):
    banner()
    run_server(host=args.host, port=args.port, open_browser=not args.no_browser)


def main():
    parser = argparse.ArgumentParser(description="Rampage (SinoWealth 258A:0016) RGB klavye kontrolü")
    sub = parser.add_subparsers(dest="command")
    level = dict(type=int, choices=range(5), metavar="0-4")

    sub.add_parser("status", help="Bağlantı ve aktif ayarları göster").set_defaults(func=cmd_status)
    sub.add_parser("list-modes", help="Tüm modları listele").set_defaults(func=cmd_list_modes)
    sub.add_parser("list-profiles", help="Kayıtlı profilleri listele").set_defaults(func=cmd_list_profiles)

    p = sub.add_parser("mode", help="Mod uygula (ör. rainbow, snake, breathing, 3)")
    p.add_argument("mode")
    p.add_argument("--speed", "-s", **level)
    p.add_argument("--brightness", "-b", **level)
    p.add_argument("--color", "-c", help="'#RRGGBB', 1-7 (palet yuvası) veya 'random'")
    d = p.add_mutually_exclusive_group()
    d.add_argument("--left", action="store_true", help="Sola doğru")
    d.add_argument("--right", action="store_true", help="Sağa doğru")
    p.set_defaults(func=cmd_mode)

    p = sub.add_parser("static", help="Tüm tuşlar tek renk")
    p.add_argument("color", nargs="?", default="#FF0000", help="#RRGGBB")
    p.add_argument("--brightness", "-b", **level)
    p.set_defaults(func=cmd_static)

    p = sub.add_parser("profile", help="Kayıtlı profili uygula")
    p.add_argument("name")
    p.set_defaults(func=cmd_profile)

    sub.add_parser("off", help="Işıkları kapat").set_defaults(func=cmd_off)
    sub.add_parser("on", help="Son modu geri aç").set_defaults(func=cmd_on)

    p = sub.add_parser("custom", help="Klavyede kayıtlı özel tuş profilini aç (1-5)")
    p.add_argument("number", type=int, choices=range(1, 6), metavar="1-5")
    p.set_defaults(func=cmd_custom)

    p = sub.add_parser("ui", help="Web arayüzünü başlat")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_ui)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

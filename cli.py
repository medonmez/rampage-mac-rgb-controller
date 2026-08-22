#!/usr/bin/env python3
"""
Rampage RGB (SinoWealth 258A:0016) Keyboard Controller CLI for macOS.
Focused on verified working hardware modes.
"""
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.driver import (
    get_driver, MODES, MODE_BY_NAME, VID, PID
)
from src.server.app import run_server, load_profiles


def print_banner():
    print("""
\033[1;35m════════════════════════════════════════════════════════════════════\033[0m
\033[1;37m   RAMPAGE RGB CONTROLLER (macOS) \033[0m• \033[1;36mSinoWealth 258A:0016\033[0m
\033[1;35m════════════════════════════════════════════════════════════════════\033[0m""")


def cmd_status(args):
    drv = get_driver()
    status = drv.get_status()
    print_banner()
    
    if status["connected"]:
        print("\033[1;32m[✓] DURUM: Klavye Bağlı ve Hazır!\033[0m")
        print(f"  • Cihaz Adı      : {status['device']['name']}")
        print(f"  • USB VID / PID  : {status['device']['vendor_id']} : {status['device']['product_id']}")
        print(f"  • Arayüz         : {status['device']['interface']}")
        print("\n\033[1;33m[Aktif Aydınlatma Ayarları]\033[0m")
        s = status["state"]
        print(f"  • Mod            : #{s['mode']} - {s.get('mode_title', s['mode_name'])}")
        print(f"  • Parlaklık      : Seviye {s['brightness']}/4 (%{s['brightness']*25})")
        print(f"  • Hız            : Seviye {s['speed']}/4")
    else:
        print("\033[1;31m[✗] DURUM: Rampage (258A:0016) klavye bulunamadı veya bağlı değil!\033[0m")
        print("  Lütfen klavyenizin USB kablosunu kontrol edin.")


def cmd_list_modes(args):
    print_banner()
    print("\n\033[1;33m[Desteklenen ve Çalışan Aydınlatma Modları]\033[0m\n")
    for m_id, m_info in MODES.items():
        name_str = f"\033[1;36m{m_info['name']:<18}\033[0m"
        title_str = m_info["title"]
        features = []
        if m_info["has_speed"]: features.append("Hız Ayarlı")
        if m_info["has_brightness"]: features.append("Parlaklık Ayarlı")
        feat_str = f"[\033[90m{', '.join(features)}\033[0m]" if features else ""
        print(f"  ID {m_id:>2} : {name_str} - {title_str:<38} {feat_str}")


def cmd_list_profiles(args):
    profiles = load_profiles()
    print_banner()
    print("\n\033[1;33m[Kayıtlı Aydınlatma Profilleri]\033[0m\n")
    for idx, p in enumerate(profiles, 1):
        default_tag = " \033[90m(Varsayılan)\033[0m" if p.get("is_default") else ""
        print(f"  {idx}. \033[1;36m{p['name']}\033[0m{default_tag}")
        print(f"     Mod: {p.get('mode')} | Parlaklık: %{p.get('brightness', 4)*25} | Hız: {p.get('speed', 2)}/4")
        if p.get("description"):
            print(f"     Açıklama: {p.get('description')}")
        print()


def cmd_mode(args):
    drv = get_driver()
    if not drv.is_connected():
        print("\033[1;31m[Hata] Klavye bağlı değil!\033[0m")
        sys.exit(1)

    mode_val = args.mode
    success = drv.set_effect(mode=mode_val, speed=args.speed, brightness=args.brightness)
    if success:
        mode_id = MODE_BY_NAME.get(mode_val.lower(), 1) if not str(mode_val).isdigit() else int(mode_val)
        m_info = MODES.get(mode_id, MODES[1])
        print(f"\033[1;32m[✓] Mod uygulandı: {m_info['title']}\033[0m")
        print(f"    Parlaklık: %{args.brightness*25} | Hız: {args.speed}/4")
    else:
        print("\033[1;31m[Hata] Mod gönderilirken donanım hatası oluştu.\033[0m")


def cmd_static(args):
    drv = get_driver()
    if not drv.is_connected():
        print("\033[1;31m[Hata] Klavye bağlı değil!\033[0m")
        sys.exit(1)

    success = drv.set_static_color(color="red", brightness=args.brightness)
    if success:
        print(f"\033[1;32m[✓] Sabit Kırmızı mod uygulandı (Parlaklık: %{args.brightness*25})\033[0m")
    else:
        print("\033[1;31m[Hata] Komut gönderilemedi.\033[0m")


def cmd_profile(args):
    drv = get_driver()
    if not drv.is_connected():
        print("\033[1;31m[Hata] Klavye bağlı değil!\033[0m")
        sys.exit(1)

    profiles = load_profiles()
    query = args.name.lower()
    target = None
    for p in profiles:
        if p.get("id", "").lower() == query or p.get("name", "").lower() == query:
            target = p
            break

    if not target:
        print(f"\033[1;31m[Hata] '{args.name}' adında bir profil bulunamadı.\033[0m")
        sys.exit(1)

    mode = target.get("mode", "rainbow")
    brightness = target.get("brightness", 4)
    speed = target.get("speed", 2)

    success = drv.set_effect(mode=mode, speed=speed, brightness=brightness)
    if success:
        print(f"\033[1;32m[✓] '{target['name']}' profili başarıyla klavyeye uygulandı!\033[0m")
    else:
        print("\033[1;31m[Hata] Profil uygulanamadı.\033[0m")


def cmd_off(args):
    drv = get_driver()
    if not drv.is_connected():
        print("\033[1;31m[Hata] Klavye bağlı değil!\033[0m")
        sys.exit(1)

    success = drv.turn_off()
    if success:
        print("\033[1;32m[✓] Klavye aydınlatması kapatıldı (Off).\033[0m")
    else:
        print("\033[1;31m[Hata] Komut gönderilemedi.\033[0m")


def cmd_ui(args):
    print_banner()
    open_browser = not args.no_browser
    run_server(host=args.host, port=args.port, open_browser=open_browser)


def main():
    parser = argparse.ArgumentParser(
        description="Rampage (SinoWealth 258A:0016) RGB Keyboard Controller for macOS",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Kullanılabilir komutlar")

    # status
    p_status = subparsers.add_parser("status", help="Klavye bağlantı ve aydınlatma durumunu gösterir")
    p_status.set_defaults(func=cmd_status)

    # list-modes
    p_modes = subparsers.add_parser("list-modes", help="Desteklenen aydınlatma modlarını listeler")
    p_modes.set_defaults(func=cmd_list_modes)

    # list-profiles
    p_profiles = subparsers.add_parser("list-profiles", help="Kayıtlı profilleri listeler")
    p_profiles.set_defaults(func=cmd_list_profiles)

    # mode
    p_mode = subparsers.add_parser("mode", help="Efekt modu ayarlar (rainbow, static, snake)")
    p_mode.add_argument("mode", help="Mod adı (rainbow, static, snake, off)")
    p_mode.add_argument("--speed", "-s", type=int, default=2, choices=[0, 1, 2, 3, 4], help="Hız (0-4)")
    p_mode.add_argument("--brightness", "-b", type=int, default=4, choices=[0, 1, 2, 3, 4], help="Parlaklık (0-4)")
    p_mode.set_defaults(func=cmd_mode)

    # static
    p_static = subparsers.add_parser("static", help="Sabit Kırmızı modu ayarlar")
    p_static.add_argument("--brightness", "-b", type=int, default=4, choices=[0, 1, 2, 3, 4], help="Parlaklık (0-4)")
    p_static.set_defaults(func=cmd_static)

    # profile
    p_profile = subparsers.add_parser("profile", help="Kayıtlı bir profili uygular")
    p_profile.add_argument("name", help="Profil adı veya ID'si")
    p_profile.set_defaults(func=cmd_profile)

    # off
    p_off = subparsers.add_parser("off", help="Klavye aydınlatmasını kapatır")
    p_off.set_defaults(func=cmd_off)

    # ui
    p_ui = subparsers.add_parser("ui", help="Web arayüzünü ve sunucusunu başlatır")
    p_ui.add_argument("--host", default="127.0.0.1", help="Sunucu adresi (Varsayılan: 127.0.0.1)")
    p_ui.add_argument("--port", type=int, default=8765, help="Port (Varsayılan: 8765)")
    p_ui.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    p_ui.set_defaults(func=cmd_ui)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        cmd_status(args)
        parser.print_help()


if __name__ == "__main__":
    main()

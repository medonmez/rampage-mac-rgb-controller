# Rampage RGB Keyboard Controller for macOS 🎮✨

SinoWealth / BY Tech üretimi USB denetleyici yongasına sahip (**VID: `0x258A` / PID: `0x0016`**) **Rampage mekanik klavyeler** için macOS üzerinde root/sudo gerektirmeden çalışan, donanım seviyesinde RGB aydınlatma kontrol uygulaması.

---

## 🌟 Özellikler

- **Sıfır Bağımlılık (Zero External Dependencies):** Harici kütüphane, C derlemesi veya kext gerektirmez. macOS'un yerleşik `IOKit.framework` ve `CoreFoundation.framework` kütüphanelerini doğrudan `ctypes` ile bağlar.
- **Güvenli IOKit Eşleşmesi:** macOS EventSystem'in klavye girdi arayüzünü (Interface 0) kilitlemesine takılmadan sadece donanımın **Vendor Feature Interface (Usage: 128 / PrimaryUsagePage: 1)** aydınlatma arayüzüyle iletişim kurar.
- **Donanım Burst İletişimi:** SinoWealth firmware'inin beklediği 5 aşamalı donanım veri dizilerini (Report ID 5 El Sıkışma + 1032 baytlık Report ID 6 veri blokları) doğru sırayla iletir.
- **Modern Türkçe Q Klavye Önizlemesi:** Glassmorphism karanlık tema, gerçek mekanik tuş düzeni (Ğ, Ü, Ş, İ, Ö, Ç) ve canlı LED animasyon simülasyonu.
- **Kalıcı Bellek & Temiz Kapanma:** Arayüzdeki *"Uygulamayı Kapat"* butonuna basıldığında sunucu kapanır, seçilen son aydınlatma modu klavyenin dahili çipinde çalışmaya devam eder.
- **Hem Web Arayüzü Hem CLI:** Terminalden tek komutla kontrol veya web tarayıcısından görsel yönetim.

---

## ⚡ Desteklenen Aydınlatma Modları

| Mod | Açıklama | Hız Ayarı | Parlaklık Ayarı |
| :--- | :--- | :---: | :---: |
| 🌈 **Gökkuşağı Dalgası (Rainbow Wave)** | Akıcı tam spektrum gökkuşağı animasyonu | ✅ | ✅ |
| 🔴 **Sabit Kırmızı (Static Red)** | Tüm tuşlar için parlak kırmızı aydınlatma | ❌ | ✅ |
| 🐍 **Retro Yılan (Retro Snake)** | Nostaljik yılan oyunu tarzı gezinme animasyonu | ✅ | ✅ |
| ⏻ **Işıkları Kapat (Off)** | Klavye LED'lerini tamamen söndürür | ❌ | ❌ |

---

## 🚀 Kurulum ve Başlatma

Herhangi bir `pip install` işlemine gerek yoktur. Python 3 kurulu olan herhangi bir macOS sisteminde doğrudan çalışır:

```bash
# Projeyi klonlayın veya dizine gidin
cd klavye-kontrol

# Web arayüzünü tek tıkla başlatın
./start.sh
```

Tarayıcınızda otomatik olarak `http://127.0.0.1:8765` adresi açılacaktır.

---

## ⌨️ Komut Satırı (CLI) Kullanımı

Terminalden hızlıca aydınlatma modlarını değiştirmek için `cli.py` veya `rampage-rgb` çalıştırılabilir:

```bash
# 1. Klavye bağlantı ve aktif mod durumunu kontrol et
python3 cli.py status

# 2. Gökkuşağı dalgası moduna geç (Hız: 3, Parlaklık: 4)
python3 cli.py mode rainbow --speed 3 --brightness 4

# 3. Sabit Kırmızı moda geç
python3 cli.py static --brightness 4

# 4. Retro Yılan animasyonuna geç
python3 cli.py mode snake --speed 2

# 5. Klavye aydınlatmasını kapat
python3 cli.py off

# 6. Desteklenen modları ve profilleri listele
python3 cli.py list-modes
python3 cli.py list-profiles
```

---

## 🏗️ Proje Mimarisi

```
klavye-kontrol/
├── cli.py                  # Terminal CLI arayüzü
├── start.sh                # Tek tıkla başlatıcı script
├── rampage-rgb             # CLI wrapper
├── src/
│   ├── driver/
│   │   ├── iokit_driver.py # macOS IOKit / IOHIDManager ctypes sürücüsü
│   │   ├── protocol.py     # SinoWealth 258a:0016 paket motoru
│   │   ├── layout.py       # Türkçe Q klavye tuş matrisi tanımları
│   │   └── templates/      # Donanım burst veri şablonları
│   ├── server/
│   │   └── app.py          # Hafif REST API ve statik dosya sunucusu
│   └── ui/
│       ├── index.html      # Modern macOS cam efektli kullanıcı arayüzü
│       ├── style.css       # Dark mode & keycap animasyon stilleri
│       └── app.js          # İnteraktif klavye canvas mantığı ve API bağlantısı
└── README.md
```

---

## 📄 Lisans
MIT License.

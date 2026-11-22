# Rampage RGB Keyboard Controller for macOS 🎮✨

SinoWealth / BY Tech üretimi USB denetleyici yongasına sahip (**VID: `0x258A` / PID: `0x0016`**) **Rampage mekanik klavyeler** için macOS üzerinde root/sudo gerektirmeden çalışan, donanım seviyesinde RGB aydınlatma kontrol uygulaması.

---

## 🌟 Özellikler

- **Sıfır bağımlılık:** Python 3 + macOS'un yerleşik `IOKit` / `CoreFoundation` kütüphaneleri (`ctypes`).
- **20 donanım efektinin tamamı:** her efektin kendi hızı (0-4), parlaklığı (0-4), yönü ve 7 renklik paleti klavyenin belleğine yazılır.
- **Oku → değiştir → yaz → doğrula:** uygulama klavyenin kendi ayar sayfasını okur, sadece ilgili baytları değiştirir, yazar ve geri okuyarak gerçekten uygulandığını kontrol eder. Fn tuşlarıyla yapılan değişiklikler arayüze yansır.
- **Protokol algılama:** 258A:0016 kimliğini kullanan iki SinoWealth varyantı var (`kb16` ve eski `f11` şablonu). Uygulama ikisini dener, geri okumada çalışanı bulup `~/.rampage_rgb_settings.json` dosyasına kaydeder.
- **Anlaşılır hata durumları:** macOS izni yoksa, klavye takılı değilse veya başka bir uygulama kullanıyorsa arayüz bunu açıkça söyler.
- **Canlı önizleme:** her efektin yaklaşık simülasyonu; fiziksel tuşlara bastığınızda tepki efektleri önizlemede de çalışır.

> **İzin:** İlk çalıştırmada macOS "Giriş İzleme" (Input Monitoring) izni isteyebilir. *Sistem Ayarları → Gizlilik ve Güvenlik → Giriş İzleme* bölümünde uygulamayı başlattığınız Terminal'i açın.

---

## ⚡ Efektler

Sabit Renk, Nefes, Gökkuşağı Dalgası, Kaybolan Işık, Yağmur Damlaları, Gökkuşağı Çarkı, Dalgacıklar, Yıldız Pırıltısı, Gölge, Retro Yılan, Neon Akış, Tepki, Sinüs Dalgası, Tarama, Yel Değirmeni, Renkli Şelale, Çiçeklenme, Dönen Fırtına, Çarpışma, Kusursuz. Liste: `python3 cli.py list-modes`.

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

## ⌨️ Komut Satırı (CLI)

```bash
python3 cli.py status                                   # bağlantı + klavyedeki gerçek ayar
python3 cli.py mode rainbow --speed 3 --brightness 4 --left
python3 cli.py mode breathing --color "#00B4FF"         # renk: #RRGGBB, 1-7 (palet) veya random
python3 cli.py static "#FF8800" -b 3                    # tüm tuşlar tek renk
python3 cli.py off / on                                 # kapat / son efekti geri aç
python3 cli.py profile red_dragon                       # kayıtlı profil
python3 cli.py protocol [auto|kb16|f11]                 # protokol varyantı
python3 cli.py list-modes / list-profiles
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

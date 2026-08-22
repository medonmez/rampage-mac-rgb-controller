#!/bin/bash
# Rampage RGB Keyboard Controller - Tek Tıkla Başlatıcı
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "======================================================"
echo "  Rampage RGB Keyboard Controller (macOS)"
echo "  SinoWealth 258A:0016 Aydınlatma Denetleyicisi"
echo "======================================================"

# Check Python3 availability
if ! command -v python3 &> /dev/null; then
    echo "[HATA] Sisteminizde Python 3 bulunamadı. Lütfen Python 3 kurun."
    exit 1
fi

echo "[1/2] Klavye donanım kontrolü yapılıyor..."
python3 cli.py status

echo ""
echo "[2/2] Web Arayüzü başlatılıyor..."
python3 cli.py ui "$@"

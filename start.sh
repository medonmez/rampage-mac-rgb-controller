#!/bin/bash
# Rampage RGB Keyboard Controller - tek tıkla başlatıcı
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
PORT="${PORT:-8765}"
URL="http://127.0.0.1:$PORT"

if ! command -v python3 &> /dev/null; then
    echo "[HATA] Python 3 bulunamadı. Lütfen Python 3 kurun."
    exit 1
fi

# Arayüz zaten çalışıyorsa sadece tarayıcıda aç
if curl -s -o /dev/null --max-time 1 "$URL/api/device/modes"; then
    echo "Rampage RGB arayüzü zaten çalışıyor: $URL"
    open "$URL"
    exit 0
fi

python3 cli.py status
echo ""
python3 cli.py ui --port "$PORT" "$@"

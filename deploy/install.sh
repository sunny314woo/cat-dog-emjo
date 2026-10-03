#!/usr/bin/env bash
set -euo pipefail
BASE=/home/wisteria/emjo
if [ "$(id -u)" != 0 ]; then
  echo '请执行 sudo bash /home/wisteria/emjo/current/deploy/install.sh，密码由你输入。'
  exit 1
fi
# Only this product's virtual environment and service are managed.
if [ ! -x "$BASE/venv/bin/python" ]; then
  sudo -u wisteria python3 -m venv "$BASE/venv"
fi
sudo -u wisteria "$BASE/venv/bin/python" -m pip install -r "$BASE/current/server/requirements.txt"
if [ ! -f /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc ]; then
  apt-get install -y fonts-noto-cjk
fi
"$BASE/venv/bin/python" "$BASE/current/deploy/install_service.py"

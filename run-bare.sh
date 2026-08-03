#!/usr/bin/env bash
cd "$(dirname "$0")"
export ER_SAVE_MANAGER_NEXUS_BUILD=1
export ER_SAVEDATA_DIR="$HOME/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing"
exec python app.py

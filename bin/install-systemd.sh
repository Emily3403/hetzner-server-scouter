#!/usr/bin/env bash
# This script is used to install the systemd service file for he application.

if [ "$EUID" -eq 0 ]; then
    echo "Please this script as a normal user."
    exit 1
fi

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

cp "$SCRIPT_DIR"/../systemd/hscout.* "$XDG_CONFIG_HOME/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now hscout.timer

echo -e "Installed systemd service files and enabled the timer!"
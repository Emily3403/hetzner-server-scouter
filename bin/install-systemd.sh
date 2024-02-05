#!/usr/bin/env bash
# This script is used to install the systemd service file for he application.

if [ "$EUID" -eq 0 ]; then
    echo "Please this script as a normal user."
    exit 1
fi

# Prompt for verification (default no)
read -p "Do you want to install the systemd service files and enable the timer? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborting..."
    exit 1
fi

if [ -z "$XDG_CONFIG_HOME" ]; then
    config_home="$HOME/.config"
else
    config_home="$XDG_CONFIG_HOME"
fi


SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

mkdir -p "$config_home/systemd/user/"
cp "$SCRIPT_DIR"/../systemd/hscout.* "$config_home/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now hscout.timer

echo -e "Installed systemd service files and enabled the timer!"
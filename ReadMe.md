# Hetzner Server Scouter

![Tests](https://github.com/Emily3403/hetzner-server-scouter/actions/workflows/tests.yml/badge.svg)

Hetzner Server Scouter is a simple tool to find and get notified about the cheapest Hetzner server that meet your exact requirements.

By default, this tool will only output the found servers to the console. However, you can also get notified via telegram (see below).

## Available Filters

The following filters are available:
- Price
- CPU name
- RAM size
- Datacenter 
  - Frankfurt
  - Helsinki
  - Nürnberg
- Disks
  - Number of disks
  - Size of each disk (or any disk)
  - Number of Fast storage devices (SSD / NVME)
  - Effective RAID size (0, 1, 5, 6)
- Specials 
  - GPU
  - iNIC
  - ECC
  - Hardware RAID

## Installation

```bash
pip install git+https://github.com/Emily3403/hetzner-server-scouter
```

## Usage

```bash
hscout --price 50
hscout --ram 32 --disk-num 4 --disk-num-quick 1
hscout --disk-num 3 --disk-size-raid5 12000
hscout --gpu --ecc --hwr
```

### Notifications

You can get notified when a new server is available. For now, only telegram support is available but this can be easily expanded in the future (pull requests welcome).

To enable telegram notifications, you need to create a [telegram bot](https://core.telegram.org/bots/tutorial). Then, you need to set the following environment variables:

```bash
TELEGRAM_BOT_TOKEN=<your bot token>
TELEGRAM_CHAT_ID=<your chat id>
```

To obtain the Chat ID, send a message to your bot follow [this](https://stackoverflow.com/a/32572159/11163194) guide.

### Systemd

Usually, you don't want to run this tool manually. Instead, you want to run it periodically and get notified if a new server is available.

Hetzner-Server-Scouter is a user service. To install it, copy the `systemd/hscout.service` and `systemd/hscout.timer` file into `$XDG_CONFIG_DIR/systemd/user` and enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable hscout.timer
```

This will then run the tool every hour. You can change this by editing the `hscout.timer` file and adjusting the `OnCalendar` property. See the [systemd documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html#OnCalendar=) for more information.

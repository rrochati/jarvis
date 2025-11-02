# Jarvis Home Automation

## Overview

Jarvis is a Python-based Telegram bot that can:
- Receive commands from Telegram
- Execute system commands on your Raspberry Pi
- Interact with existing applications
- Send responses back to Telegram


## Setup Instructions

1. **Get your bot token:**
- Message @BotFather on Telegram
- Create a new bot with `/newbot`
- Save the token

2. **Get your user ID:**
- Message @userinfobot on Telegram to get your user ID

3. **Install and configure:**
- Install required python packages:
    ```bash
    conda activate python311
    pip3 install python-telegram-bot psutil
    ```

- Set env variables:
    ```bash
    export TELEGRAM_BOT_TOKEN=YOUR_TOKEN
    export AUTHORIZED_USERS="USER_IDs"
    export LOG_FILE="/home/rrocha/logs/jarvis.log"
    ```

- Create logs directory:
    ```bash
    mkdir -p /home/rrocha/logs
    ```

4. **Test run**
    ```bash
    python3 jarvis.py start
    ```

5. **Set up as systemd service:**
- Set up .env:
Copy .env.example as .env and edit it for your values.

    ```bash
    # Set secure permissions
    chmod 600 /home/rrocha/jarvis/.env
    chown rrocha:rrocha /home/rrocha/jarvis/.env

    # Make sure it's not tracked by git
    echo ".env" >> /home/rrocha/jarvis/.gitignore
    ```

- Copy service file to systemd:
    ```bash
    sudo cp /home/rrocha/jarvis/jarvis-wrapper.service /etc/systemd/system/jarvis-bot.service
    ```

- Enable and start the service:
    ```bash
    # Reload systemd configuration
    sudo systemctl daemon-reload

    # Enable service to start at boot
    sudo systemctl enable jarvis-bot.service

    # Start the service
    sudo systemctl start jarvis-bot.service
    ```

- Service Management Commands
Once set up, you can control your service with:
    ```bash
    # Start the service
    sudo systemctl start jarvis-bot.service

    # Stop the service
    sudo systemctl stop jarvis-bot.service

    # Restart the service
    sudo systemctl restart jarvis-bot.service

    # Reload configuration (if the service supports it)
    sudo systemctl reload jarvis-bot.service

    # Check status
    sudo systemctl status jarvis-bot.service

    # View logs
    sudo journalctl -u jarvis-bot.service -f

    # View recent logs
    sudo journalctl -u jarvis-bot.service --since "1 hour ago"
    ```
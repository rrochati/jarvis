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

4. ***Test run***
   ```bash
   python3 jarvis.py start
   ```

5. **Set up as service (optional):**
   ```bash
   sudo cp telegram-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable telegram-bot
   sudo systemctl start telegram-bot
   ```




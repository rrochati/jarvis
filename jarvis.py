import logging
import subprocess
import psutil
import os, sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

LOG_FILE=os.getenv('LOG_FILE', '/home/rrocha/jarvis/jarvis.log')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),  # This ensures output goes to stdout
        logging.FileHandler(LOG_FILE, mode='a') # Send logs to file
    ]
)
logger = logging.getLogger(__name__)

# Replace with your bot token from BotFather
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Replace with your Telegram user ID for security (optional)
AUTHORIZED_USERS = [int(x) for x in os.getenv('AUTHORIZED_USERS', '').split(',') if x.strip()]

# Application management
MANAGED_APPS = {
    'station': 'weather-station',
    'jarvis': 'jarvis',
    'database': 'postgresql'
}

# Safe commands for /run
SAFE_COMMANDS = ['df', 'free', 'uptime', 'date', 'systemctl status']

def is_authorized(user_id):
    """Check if user is authorized to use the bot"""
    return user_id in AUTHORIZED_USERS if AUTHORIZED_USERS else True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized access!")
        return
    
    welcome_text = """
🤖 Raspberry Pi Bot is online!

Available commands:
/status - System status
/apps - List running applications
/restart_app <name> - Restart an application
/run <command> - Execute system command
/temp - CPU temperature
/uptime - System uptime
/help - Show this help message
"""
    await update.message.reply_text(welcome_text)

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get system status information"""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Temperature (Raspberry Pi specific)
        try:
            temp_result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                       capture_output=True, text=True)
            temp = temp_result.stdout.strip().replace('temp=', '').replace("'C", "°C")
        except:
            temp = "N/A"
        
        status_text = f"""
    📊 **System Status**

    🖥️ CPU Usage: {cpu_percent}%
    🧠 Memory: {memory.percent}% ({memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB)
    💾 Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)
    🌡️ Temperature: {temp}
    """
        await update.message.reply_text(status_text)
        
    except Exception as e:
        await update.message.reply_text(f"Error getting system status: {str(e)}")

async def list_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List running applications"""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                proc_info = proc.info
                if proc_info['cpu_percent'] > 0 or proc_info['name'] in ['python3', 'node', 'nginx', 'apache2']:
                    processes.append(f"• {proc_info['name']} (PID: {proc_info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if processes:
            app_list = "🔄 **Running Applications:**\n\n" + "\n".join(processes[:20])
        else:
            app_list = "No notable applications running"
            
        await update.message.reply_text(app_list)
        
    except Exception as e:
        await update.message.reply_text(f"Error listing applications: {str(e)}")

async def restart_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart a specific application"""
    if not is_authorized(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /restart_app <application_name>")
        return
    
    app_name = " ".join(context.args)
    
    try:
        # This is a basic example - you might need to customize based on your apps
        # Using systemctl for services
        result = subprocess.run(['sudo', 'systemctl', 'restart', app_name], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            await update.message.reply_text(f"✅ Successfully restarted {app_name}")
        else:
            await update.message.reply_text(f"❌ Failed to restart {app_name}: {result.stderr}")
            
    except Exception as e:
        await update.message.reply_text(f"Error restarting application: {str(e)}")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute a system command"""
    if not is_authorized(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /run <command>")
        return
    
    command = " ".join(context.args)
    
    # Security: Only allow safe commands
    safe_commands = SAFE_COMMANDS
    if not any(command.startswith(cmd) for cmd in safe_commands):
        await update.message.reply_text("❌ Command not allowed for security reasons")
        return
    
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, timeout=10)
        
        output = result.stdout if result.stdout else result.stderr
        if len(output) > 4000:  # Telegram message limit
            output = output[:4000] + "... (truncated)"
            
        await update.message.reply_text(f"```\n{output}\n```", parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Command timed out")
    except Exception as e:
        await update.message.reply_text(f"❌ Error executing command: {str(e)}")

async def get_temperature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get CPU temperature"""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
        temp = result.stdout.strip().replace('temp=', '').replace("'C", "°C")
        await update.message.reply_text(f"🌡️ CPU Temperature: {temp}")
    except Exception as e:
        await update.message.reply_text(f"Error getting temperature: {str(e)}")

async def get_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get system uptime"""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        result = subprocess.run(['uptime'], capture_output=True, text=True)
        await update.message.reply_text(f"⏰ {result.stdout.strip()}")
    except Exception as e:
        await update.message.reply_text(f"Error getting uptime: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = """
    🤖 **Raspberry Pi Bot Commands:**

    /start - Start the bot
    /status - Get system status (CPU, memory, disk, temp)
    /apps - List running applications
    /restart_app <name> - Restart a systemd service
    /run <command> - Execute safe system commands
    /temp - Get CPU temperature
    /uptime - Get system uptime
    /help - Show this help message

    **Security:** Only authorized users can use this bot.
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages"""
    if not is_authorized(update.effective_user.id):
        return
    
    await update.message.reply_text("Use /help to see available commands!")

async def custom_app_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control your specific applications"""
    # First check if we can reply
    if not update or not update.effective_message:
        logger.error("Update or message is None")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /app <start|stop|status> <app_name>")
        return
    
    action = context.args[0]
    app_name = context.args[1] if len(context.args) > 1 else None
    
    # Validate actions
    valid_actions = {'start', 'stop', 'status'}
    if action not in valid_actions:
        await update.effective_message.reply_text("❌ Invalid action. Use start, stop, or status.")
        return
    
    # Validate app names
    valid_apps = {'weather-station'}  # Add your allowed apps here
    if app_name not in valid_apps:
        await update.effective_message.reply_text("❌ Invalid application name")
        return
    
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', action, app_name],
            capture_output=True,
            text=True,
            timeout=10,
            check=True  # Raise CalledProcessError if command fails
        )
        
        output = result.stdout if result.stdout else result.stderr
        if len(output) > 4000:
            output = output[:4000] + "... (truncated)"
            
        await update.effective_message.reply_text(f"```\n{output}\n```", parse_mode='Markdown')
    
    except subprocess.TimeoutExpired:
        await update.effective_message.reply_text("❌ Command timed out")
    except subprocess.CalledProcessError as e:
        await update.effective_message.reply_text(f"❌ Command failed with exit code {e.returncode}")
    except Exception as e:
        logger.error(f"Error in custom_app_control: {str(e)}", exc_info=True)
        try:
            await update.effective_message.reply_text(f"❌ Error executing command: {str(e)}")
        except Exception as reply_error:
            logger.error(f"Could not send error message: {str(reply_error)}", exc_info=True)

def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the dispatcher"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Try to notify user
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            update.effective_message.reply_text("❌ Sorry, something went wrong!")
        except Exception as e:
            logger.error(f"Could not send error message: {str(e)}", exc_info=True)

def main():
    """Start the bot."""
    logger.info("Starting Raspberry Pi Bot")
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", system_status))
    application.add_handler(CommandHandler("apps", list_apps))
    application.add_handler(CommandHandler("restart_app", restart_app))
    application.add_handler(CommandHandler("app", custom_app_control))
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("temp", get_temperature))
    application.add_handler(CommandHandler("uptime", get_uptime))
    application.add_handler(CommandHandler("help", help_command))
    
    # Handle all non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot started. Listening for commands...")
    application.run_polling()

if __name__ == '__main__':
    main()

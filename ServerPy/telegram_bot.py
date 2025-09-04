from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.utils.request import Request
from interactor import ESP32Interactor
import requests
import random
import time
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ESP setup
esp = ESP32Interactor()

# Device and pin mapping
DEVICE_PINS = {
    "light": 13,
    "fan": 14,
    "door": 27
}

COMMAND_MAP = {
    "turn on light": ("light", 1),
    "turn off light": ("light", 0),
    "turn on fan": ("fan", 1),
    "turn off fan": ("fan", 0),
    "open door": ("door", 1),
    "close door": ("door", 0),
}

class ProxyManager:
    def __init__(self):
        # Free proxy lists - these change frequently, so update regularly
        self.http_proxies = [
            'http://103.152.112.145:80',
            'http://185.162.251.76:41890',
            'http://103.143.63.210:3128',
            'http://185.15.172.212:3128',
            'http://103.149.162.194:80',
            'http://103.105.54.26:8080',
        ]
        
        self.socks5_proxies = [
            'socks5://103.85.232.20:1080',
            'socks5://103.75.190.169:58593',
            'socks5://72.195.34.42:4145',
            'socks5://98.170.57.231:4145',
            'socks5://184.178.172.14:4145',
            'socks5://72.221.164.34:60671',
        ]
        
        self.socks4_proxies = [
            'socks4://103.85.232.20:1080',
            'socks4://103.75.190.169:58593',
            'socks4://72.195.34.42:4145',
            'socks4://98.170.57.231:4145',
        ]
        
        self.all_proxies = self.http_proxies + self.socks5_proxies + self.socks4_proxies
        self.working_proxies = []
        self.current_proxy = None
    
    def test_proxy(self, proxy_url, timeout=10):
        """Test if a proxy is working"""
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            response = requests.get(
                'https://httpbin.org/ip', 
                proxies=proxies, 
                timeout=timeout
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Proxy {proxy_url} is working")
                return True
            else:
                logger.warning(f"❌ Proxy {proxy_url} returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"❌ Proxy {proxy_url} failed: {str(e)}")
            return False
    
    def find_working_proxies(self, max_test=10):
        """Find working proxies from the list"""
        logger.info("🔍 Testing proxies...")
        self.working_proxies = []
        
        # Shuffle and test a subset
        test_proxies = random.sample(self.all_proxies, min(max_test, len(self.all_proxies)))
        
        for proxy in test_proxies:
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
                if len(self.working_proxies) >= 3:  # Stop after finding 3 working proxies
                    break
        
        logger.info(f"✅ Found {len(self.working_proxies)} working proxies")
        return self.working_proxies
    
    def get_working_proxy(self):
        """Get a working proxy, test if needed"""
        if not self.working_proxies:
            self.find_working_proxies()
        
        if self.working_proxies:
            self.current_proxy = random.choice(self.working_proxies)
            return self.current_proxy
        
        return None
    
    def remove_broken_proxy(self, proxy_url):
        """Remove a broken proxy from working list"""
        if proxy_url in self.working_proxies:
            self.working_proxies.remove(proxy_url)
            logger.info(f"🗑️ Removed broken proxy: {proxy_url}")
    
    def fetch_fresh_proxies(self):
        """Fetch fresh proxies from free proxy APIs"""
        try:
            # Free proxy API services
            apis = [
                'https://www.proxy-list.download/api/v1/get?type=http',
                'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=5000&country=all',
                'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
            ]
            
            fresh_proxies = []
            
            for api_url in apis[:1]:  # Test only first API to avoid rate limiting
                try:
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        for proxy in proxies[:10]:  # Take first 10
                            if ':' in proxy and proxy.count('.') == 3:
                                fresh_proxies.append(f'http://{proxy.strip()}')
                        break
                except Exception as e:
                    logger.warning(f"Failed to fetch from {api_url}: {e}")
                    continue
            
            if fresh_proxies:
                logger.info(f"📥 Fetched {len(fresh_proxies)} fresh proxies")
                self.http_proxies.extend(fresh_proxies[:5])  # Add top 5
                self.all_proxies.extend(fresh_proxies[:5])
                
        except Exception as e:
            logger.error(f"Error fetching fresh proxies: {e}")

def create_telegram_updater(token, proxy_manager, max_retries=3):
    """Create Telegram updater with proxy support and retry logic"""
    
    for attempt in range(max_retries):
        try:
            proxy_url = proxy_manager.get_working_proxy()
            
            if not proxy_url:
                logger.warning("⚠️ No working proxies found, trying without proxy...")
                # Try without proxy
                request = Request(con_pool_size=8)
                updater = Updater(token=token, use_context=True, request=request)
                logger.info("✅ Connected to Telegram without proxy")
                return updater
            
            logger.info(f"🔄 Attempt {attempt + 1}: Trying proxy {proxy_url}")
            
            # Configure request with proxy
            request = Request(
                proxy_url=proxy_url,
                con_pool_size=8,
                connect_timeout=30,
                read_timeout=30
            )
            
            updater = Updater(
                token=token, 
                use_context=True, 
                request=request
            )
            
            # Test the connection
            bot_info = updater.bot.get_me()
            logger.info(f"✅ Connected to Telegram via proxy {proxy_url}")
            logger.info(f"🤖 Bot info: {bot_info.first_name} (@{bot_info.username})")
            
            return updater
            
        except Exception as e:
            logger.error(f"❌ Failed with proxy {proxy_url}: {str(e)}")
            proxy_manager.remove_broken_proxy(proxy_url)
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in 5 seconds...")
                time.sleep(5)
            
    logger.error("❌ All proxy attempts failed")
    return None

def start(update, context):
    update.message.reply_text("🤖 Hello! I can control your ESP32.\n\n"
                              "Try commands like:\n"
                              "`turn on light`\n"
                              "`turn off fan`\n"
                              "`open door`\n\n"
                              "Commands:\n"
                              "/status - Check device status\n"
                              "/proxy - Check proxy status\n"
                              "/refresh - Refresh proxy list", 
                              parse_mode="Markdown")

def status(update, context):
    try:
        states = esp.get_all_pin_states()
        response = "📊 **Device Status:**\n\n"
        for device, pin in DEVICE_PINS.items():
            state = states.get(pin, -1)
            status_text = "ON ✅" if state == 1 else "OFF ❌" if state == 0 else "Error ❗"
            response += f"• {device.capitalize()}: {status_text}\n"
        update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text(f"⚠️ Error fetching status: {e}")

def proxy_status(update, context):
    """Show current proxy status"""
    proxy_manager = context.bot_data.get('proxy_manager')
    if proxy_manager:
        current = proxy_manager.current_proxy or "None"
        working_count = len(proxy_manager.working_proxies)
        total_count = len(proxy_manager.all_proxies)
        
        response = f"🌐 **Proxy Status:**\n\n"
        response += f"• Current: `{current}`\n"
        response += f"• Working proxies: {working_count}\n"
        response += f"• Total proxies: {total_count}\n"
        
        update.message.reply_text(response, parse_mode="Markdown")
    else:
        update.message.reply_text("❌ Proxy manager not found")

def refresh_proxies(update, context):
    """Refresh proxy list"""
    update.message.reply_text("🔄 Refreshing proxy list...")
    
    proxy_manager = context.bot_data.get('proxy_manager')
    if proxy_manager:
        proxy_manager.fetch_fresh_proxies()
        working_proxies = proxy_manager.find_working_proxies()
        
        update.message.reply_text(f"✅ Found {len(working_proxies)} working proxies")
    else:
        update.message.reply_text("❌ Proxy manager not found")

def handle_text(update, context):
    user_command = update.message.text.lower()
    for phrase, (device, state) in COMMAND_MAP.items():
        if phrase in user_command:
            try:
                pin = DEVICE_PINS[device]
                esp.set_pin_state(pin, state)
                status_emoji = "🔛" if state else "🔴"
                update.message.reply_text(f"{status_emoji} {device.capitalize()} turned {'ON' if state else 'OFF'}")
                return
            except Exception as e:
                update.message.reply_text(f"❌ Failed to control {device}: {e}")
                return
    
    # Suggest similar commands
    suggestions = []
    for phrase in COMMAND_MAP.keys():
        if any(word in phrase for word in user_command.split()):
            suggestions.append(phrase)
    
    if suggestions:
        response = "❓ Did you mean:\n" + "\n".join([f"• `{s}`" for s in suggestions[:3]])
        update.message.reply_text(response, parse_mode="Markdown")
    else:
        update.message.reply_text("❓ I didn't understand that. Try /start for help.")

def error_handler(update, context):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    TELEGRAM_TOKEN = "7690148823:AAEhjbUkqxDNxndWBp1YT-Pukc6wBBANNk8"  # Replace with your bot token
    
    # Initialize proxy manager
    proxy_manager = ProxyManager()
    
    # Fetch fresh proxies
    logger.info("🔄 Fetching fresh proxies...")
    proxy_manager.fetch_fresh_proxies()
    
    # Create updater with proxy support
    updater = create_telegram_updater(TELEGRAM_TOKEN, proxy_manager)
    
    if not updater:
        logger.error("❌ Failed to create Telegram updater")
        return
    
    # Store proxy manager in bot data
    updater.dispatcher.bot_data['proxy_manager'] = proxy_manager
    
    # Add handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("proxy", proxy_status))
    dp.add_handler(CommandHandler("refresh", refresh_proxies))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_error_handler(error_handler)

    logger.info("🚀 Telegram bot is starting...")
    
    try:
        updater.start_polling(poll_interval=2.0, timeout=30)
        logger.info("✅ Bot is running!")
        updater.idle()
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")
        
        # Try to restart with a different proxy
        logger.info("🔄 Attempting to restart with different proxy...")
        proxy_manager.remove_broken_proxy(proxy_manager.current_proxy)
        
        # Recursive retry (be careful with this)
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
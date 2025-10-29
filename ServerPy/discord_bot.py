import discord
from discord.ext import commands
from discord.ui import Button, View
from interactor import ESP32Interactor
import logging
from pathlib import Path

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

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

class DeviceControlView(View):
    def __init__(self, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.device_states = {}
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current device states"""
        try:
            states = esp.get_all_pin_states()
            for device, pin in DEVICE_PINS.items():
                self.device_states[device] = states.get(pin, 0)
        except Exception as e:
            logger.error(f"Error getting states: {e}")
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the user who created the view to interact"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This control panel is not for you! Use `!control` to get your own.",
                ephemeral=True
            )
            return False
        return True
    
    def get_button_style(self, device):
        """Get button style based on device state"""
        state = self.device_states.get(device, 0)
        return discord.ButtonStyle.success if state == 1 else discord.ButtonStyle.secondary
    
    def get_button_label(self, device):
        """Get button label based on device state"""
        state = self.device_states.get(device, 0)
        emoji = "🟢" if state == 1 else "⚫"
        status = "ON" if state == 1 else "OFF"
        return f"{emoji} {device.capitalize()} - {status}"
    
    @discord.ui.button(label="💡 Light", style=discord.ButtonStyle.secondary, row=0)
    async def light_button(self, interaction: discord.Interaction, button: Button):
        await self.toggle_device(interaction, "light", button)
    
    @discord.ui.button(label="🌀 Fan", style=discord.ButtonStyle.secondary, row=0)
    async def fan_button(self, interaction: discord.Interaction, button: Button):
        await self.toggle_device(interaction, "fan", button)
    
    @discord.ui.button(label="🚪 Door", style=discord.ButtonStyle.secondary, row=0)
    async def door_button(self, interaction: discord.Interaction, button: Button):
        await self.toggle_device(interaction, "door", button)
    
    @discord.ui.button(label="🔄 Refresh Status", style=discord.ButtonStyle.primary, row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        self.update_buttons()
        
        # Update button labels and styles
        for item in self.children:
            if isinstance(item, Button) and item.label != "🔄 Refresh Status" and item.label != "❌ Close":
                device = item.label.split()[1].lower()
                if device in DEVICE_PINS:
                    item.label = self.get_button_label(device)
                    item.style = self.get_button_style(device)
        
        embed = self.create_status_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("✅ Control panel closed.", ephemeral=True)
        self.stop()
        await interaction.message.delete()
    
    async def toggle_device(self, interaction: discord.Interaction, device: str, button: Button):
        """Toggle device state"""
        try:
            pin = DEVICE_PINS[device]
            current_state = self.device_states.get(device, 0)
            new_state = 1 if current_state == 0 else 0
            
            # Control the device
            esp.set_pin_state(pin, new_state)
            self.device_states[device] = new_state
            
            # Update button
            button.label = self.get_button_label(device)
            button.style = self.get_button_style(device)
            
            # Send feedback
            action = "turned ON 🟢" if new_state == 1 else "turned OFF ⚫"
            await interaction.response.send_message(
                f"✅ {device.capitalize()} {action}",
                ephemeral=True
            )
            
            # Update the embed
            embed = self.create_status_embed()
            await interaction.message.edit(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error toggling {device}: {e}")
            await interaction.response.send_message(
                f"❌ Failed to control {device}: {str(e)}",
                ephemeral=True
            )
    
    def create_status_embed(self):
        """Create status embed"""
        embed = discord.Embed(
            title="🎛️ ESP32 Device Control Panel",
            description="Click buttons below to control your devices",
            color=discord.Color.blue()
        )
        
        for device, pin in DEVICE_PINS.items():
            state = self.device_states.get(device, 0)
            status_emoji = "🟢 ON" if state == 1 else "⚫ OFF"
            embed.add_field(
                name=f"{'💡' if device == 'light' else '🌀' if device == 'fan' else '🚪'} {device.capitalize()}",
                value=status_emoji,
                inline=True
            )
        
        embed.set_footer(text="💡 Tip: Click buttons to toggle devices • 🔄 Refresh to update status")
        return embed

class QuickActionView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your control panel!",
                ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="💡 All Lights ON", style=discord.ButtonStyle.success, row=0)
    async def all_on_button(self, interaction: discord.Interaction, button: Button):
        try:
            for device, pin in DEVICE_PINS.items():
                esp.set_pin_state(pin, 1)
            await interaction.response.send_message("✅ All devices turned ON!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    @discord.ui.button(label="⚫ All Lights OFF", style=discord.ButtonStyle.secondary, row=0)
    async def all_off_button(self, interaction: discord.Interaction, button: Button):
        try:
            for device, pin in DEVICE_PINS.items():
                esp.set_pin_state(pin, 0)
            await interaction.response.send_message("✅ All devices turned OFF!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.event
async def on_ready():
    logger.info(f'✅ Bot is ready! Logged in as {bot.user.name} ({bot.user.id})')
    logger.info(f'🤖 Connected to {len(bot.guilds)} server(s)')
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="ESP32 devices | !control"
    ))

@bot.command(name='control', aliases=['panel', 'c'])
async def control(ctx):
    """Open interactive control panel"""
    view = DeviceControlView(ctx.author.id)
    embed = view.create_status_embed()
    
    await ctx.send(
        embed=embed,
        view=view,
        ephemeral=False  # Set to True if you want only the user to see it
    )

@bot.command(name='quick', aliases=['q'])
async def quick(ctx):
    """Quick actions panel"""
    view = QuickActionView(ctx.author.id)
    
    embed = discord.Embed(
        title="⚡ Quick Actions",
        description="Control all devices at once",
        color=discord.Color.gold()
    )
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='status', aliases=['s'])
async def status(ctx):
    """Check status of all devices"""
    try:
        states = esp.get_all_pin_states()
        
        embed = discord.Embed(
            title="📊 Device Status",
            description="Current status of all devices",
            color=discord.Color.green()
        )
        
        for device, pin in DEVICE_PINS.items():
            state = states.get(pin, -1)
            
            if state == 1:
                status_text = "🟢 ON"
                color = "🟢"
            elif state == 0:
                status_text = "⚫ OFF"
                color = "⚫"
            else:
                status_text = "⚠️ Error"
                color = "🟡"
            
            icon = "💡" if device == "light" else "🌀" if device == "fan" else "🚪"
            
            embed.add_field(
                name=f"{icon} {device.capitalize()}",
                value=status_text,
                inline=True
            )
        
        embed.set_footer(text="Use !control for interactive panel")
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        embed = discord.Embed(
            title="⚠️ Error",
            description=f"Failed to fetch device status: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='help', aliases=['h', 'commands'])
async def help_command(ctx):
    """Show help information"""
    embed = discord.Embed(
        title="🤖 ESP32 Control Bot - Help",
        description="Interactive control panel for your ESP32 devices",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎛️ Main Commands",
        value=(
            "`!control` or `!c` - Open interactive control panel\n"
            "`!quick` or `!q` - Quick actions (all on/off)\n"
            "`!status` or `!s` - Check device status\n"
            "`!help` or `!h` - Show this help"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💡 How to Use",
        value=(
            "1️⃣ Type `!control` to open the control panel\n"
            "2️⃣ Click buttons to toggle devices\n"
            "3️⃣ Use 🔄 Refresh to update status\n"
            "4️⃣ Click ❌ Close when done"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔒 Privacy",
        value="Only you can use your control panel. Others need to create their own!",
        inline=False
    )
    
    embed.set_footer(text="💡 Tip: Buttons show real-time device states")
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    logger.error(f"Command error: {error}")
    
    embed = discord.Embed(
        title="❌ Error",
        description=f"An error occurred: {str(error)}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

def load_env(key:str="DIS_TKN"):
    datas = {}
    with open(Path(__file__).parent/".env","r") as fp:
        for lin in fp.readlines():
            name,value = lin.strip().split("=")
            datas[name]=value
    return datas[key]

def main():
    DISCORD_TOKEN = load_env("DIS_TKN")
    
    logger.info("🚀 Starting Discord bot...")
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
🍌 BANANA NFT - Premium Telegram Bot
Minimalist design, Stars only, English language
"""

import asyncio
import logging
import json
import os
import io
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    BufferedInputFile
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============ CONFIGURATION ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # Your Telegram ID

DB_FILE = "banana_nft_db.json"

# ============ COLORS & STYLE ============
class Colors:
    """Minimalist color palette"""
    BLACK = (18, 18, 18)
    WHITE = (250, 250, 250)
    GOLD = (255, 200, 0)
    DARK_GOLD = (200, 160, 0)
    YELLOW = (255, 225, 53)
    GRAY = (40, 40, 40)
    LIGHT_GRAY = (60, 60, 60)

class Emoji:
    """Emoji set"""
    BANANA = "🍌"
    STAR = "⭐"
    GEM = "💎"
    TROPHY = "🏆"
    CROWN = "👑"
    FIRE = "🔥"
    ROCKET = "🚀"
    DIAMOND = "💎"
    COIN = "🪙"
    GIFT = "🎁"
    CHART = "📈"
    USER = "👤"
    BACK = "↩️"
    SETTINGS = "⚙️"

# ============ INITIALIZATION ============
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============ DATABASE ============
class Database:
    def __init__(self):
        self.data = self.load()
    
    def load(self):
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        
        return {
            "users": {},
            "total_stars": 0,
            "settings": {"min_donation": 10},
            "events": []
        }
    
    def save(self):
        try:
            with open(DB_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except:
            pass
    
    def get_user(self, user_id: int, username: str = ""):
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "id": user_id,
                "username": username or "",
                "total_stars": 0,
                "donations": [],
                "level": 1,
                "rank": "New Banana",
                "xp": 0,
                "join_date": datetime.now().isoformat()
            }
            self.save()
        return self.data["users"][uid]
    
    def update_user(self, user_id: int, stars: int, username: str = ""):
        user = self.get_user(user_id, username)
        user["total_stars"] += stars
        user["donations"].append({
            "stars": stars,
            "date": datetime.now().isoformat()
        })
        
        # Update level (100 stars = 1 level)
        user["level"] = user["total_stars"] // 100 + 1
        user["xp"] = user["total_stars"] % 100
        
        # Update rank
        user["rank"] = self.get_rank(user["total_stars"])
        
        # Update total
        self.data["total_stars"] += stars
        self.save()
        
        return user["rank"], user["level"]
    
    def get_rank(self, total_stars: int) -> str:
        ranks = [
            (0, "🌱 Seed"),
            (100, "🌿 Sprout"),
            (500, "🍌 Banana"),
            (1000, "⭐ Star"),
            (5000, "🏆 Champion"),
            (10000, "👑 King"),
            (50000, "🚀 Legend"),
            (100000, "💎 Immortal")
        ]
        
        for threshold, name in reversed(ranks):
            if total_stars >= threshold:
                return name
        return "🌱 Seed"
    
    def get_top_users(self, limit: int = 10):
        users = list(self.data["users"].values())
        return sorted(users, key=lambda x: x["total_stars"], reverse=True)[:limit]
    
    def get_user_position(self, user_id: int):
        top = self.get_top_users(len(self.data["users"]))
        for i, user in enumerate(top, 1):
            if user["id"] == user_id:
                return i
        return len(top) + 1

db = Database()

# ============ IMAGE GENERATION ============
class MinimalistImage:
    @staticmethod
    def generate_welcome(name: str) -> io.BytesIO:
        """Generate minimalist welcome image"""
        width, height = 800, 400
        
        # Create dark gradient background
        img = Image.new('RGB', (width, height), Colors.BLACK)
        draw = ImageDraw.Draw(img)
        
        # Add subtle pattern
        for i in range(20):
            x = i * 40
            draw.rectangle([x, 0, x + 20, height], 
                         fill=Colors.GRAY, width=0)
        
        # Add blur effect
        img = img.filter(ImageFilter.GaussianBlur(radius=2))
        draw = ImageDraw.Draw(img)
        
        # Add title
        try:
            font_large = ImageFont.truetype("arialbd.ttf", 64)
            font_medium = ImageFont.truetype("arial.ttf", 32)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        # Main title
        draw.text((width//2, 120), "BANANA NFT", 
                 font=font_large, fill=Colors.GOLD, anchor="mm")
        
        # Subtitle
        draw.text((width//2, 200), f"Welcome, {name}", 
                 font=font_medium, fill=Colors.WHITE, anchor="mm")
        
        # Decorative banana
        draw.text((width//2, 280), "🍌", 
                 font=font_large, fill=Colors.YELLOW, anchor="mm")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_achievement(username: str, stars: int, rank: str) -> io.BytesIO:
        """Generate achievement image"""
        width, height = 800, 400
        
        # Gold gradient background
        img = Image.new('RGB', (width, height), Colors.GOLD)
        draw = ImageDraw.Draw(img)
        
        try:
            font_large = ImageFont.truetype("arialbd.ttf", 56)
            font_medium = ImageFont.truetype("arial.ttf", 36)
            font_small = ImageFont.truetype("arial.ttf", 24)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Achievement text
        draw.text((width//2, 80), "ACHIEVEMENT UNLOCKED", 
                 font=font_large, fill=Colors.BLACK, anchor="mm")
        
        # Username
        draw.text((width//2, 160), f"@{username}", 
                 font=font_medium, fill=Colors.WHITE, anchor="mm")
        
        # Stars
        draw.text((width//2, 220), f"{stars} {Emoji.STAR}", 
                 font=font_large, fill=Colors.DARK_GOLD, anchor="mm")
        
        # Rank
        draw.text((width//2, 290), rank, 
                 font=font_small, fill=Colors.BLACK, anchor="mm")
        
        # Footer
        draw.text((width//2, 350), "banananftbot", 
                 font=font_small, fill=Colors.BLACK, anchor="mm")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        return buffer

# ============ KEYBOARDS ============
def main_menu() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    buttons = [
        [InlineKeyboardButton(text=f"{Emoji.COIN} Donate", callback_data="donate")],
        [InlineKeyboardButton(text=f"{Emoji.TROPHY} Leaderboard", callback_data="top")],
        [InlineKeyboardButton(text=f"{Emoji.USER} Profile", callback_data="profile")],
        [InlineKeyboardButton(text=f"{Emoji.GIFT} Rewards", callback_data="rewards")],
        [InlineKeyboardButton(text=f"{Emoji.CHART} Stats", callback_data="stats")],
        [InlineKeyboardButton(text=f"{Emoji.SETTINGS} Admin", callback_data="admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def donate_menu() -> InlineKeyboardMarkup:
    """Donation amounts"""
    buttons = [
        [
            InlineKeyboardButton(text=f"10 {Emoji.STAR}", callback_data="donate_10"),
            InlineKeyboardButton(text=f"50 {Emoji.STAR}", callback_data="donate_50"),
            InlineKeyboardButton(text=f"100 {Emoji.STAR}", callback_data="donate_100")
        ],
        [
            InlineKeyboardButton(text=f"500 {Emoji.STAR}", callback_data="donate_500"),
            InlineKeyboardButton(text=f"1000 {Emoji.STAR}", callback_data="donate_1000"),
            InlineKeyboardButton(text=f"Custom", callback_data="donate_custom")
        ],
        [InlineKeyboardButton(text=f"{Emoji.BACK} Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_menu(user_id: int, stars: int) -> InlineKeyboardMarkup:
    """Payment buttons"""
    pay_url = f"https://t.me/donate?start=banana_{user_id}_{stars}"
    
    buttons = [
        [InlineKeyboardButton(text=f"{Emoji.GEM} Pay with Stars", url=pay_url)],
        [
            InlineKeyboardButton(text=f"✅ Paid", callback_data=f"paid_{user_id}"),
            InlineKeyboardButton(text=f"🔄 Status", callback_data=f"status_{user_id}")
        ],
        [InlineKeyboardButton(text=f"{Emoji.BACK} Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ============ STATES ============
class DonationState(StatesGroup):
    waiting_amount = State()
    processing = State()

# ============ HANDLERS ============
@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Start command with minimalist design"""
    user = db.get_user(message.from_user.id, message.from_user.username)
    
    # Generate welcome image
    img_buffer = MinimalistImage.generate_welcome(
        message.from_user.first_name or message.from_user.username or "Friend"
    )
    
    welcome_text = f"""
{Emoji.BANANA} **BANANA NFT**

*Welcome to the most exclusive NFT community on Telegram.*

**Your Status:**
{Emoji.USER} Rank: *{user['rank']}*
{Emoji.STAR} Stars: *{user['total_stars']}*
{Emoji.FIRE} Level: *{user['level']}*

**Total Community Stars:** {db.data['total_stars']:,}

*Elegant. Minimal. Powerful.*
    """
    
    try:
        await message.answer_photo(
            photo=BufferedInputFile(img_buffer.getvalue(), filename="welcome.png"),
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    except:
        await message.answer(
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

@dp.callback_query(F.data == "donate")
async def donate_handler(callback: types.CallbackQuery):
    """Donation menu"""
    user = db.get_user(callback.from_user.id)
    
    text = f"""
{Emoji.GEM} **SUPPORT BANANA NFT**

Support our journey and unlock exclusive rewards.

**Your Contribution:** {user['total_stars']} {Emoji.STAR}
**Your Rank:** {user['rank']}

**Select amount:**
• 10+ {Emoji.STAR} → Exclusive emoji pack
• 100+ {Emoji.STAR} → VIP status
• 1000+ {Emoji.STAR} → Golden Banana NFT
• 5000+ {Emoji.STAR} → Diamond membership

*Every star counts. Every star matters.*
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=donate_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("donate_"))
async def quick_donate(callback: types.CallbackQuery, state: FSMContext):
    """Quick donation"""
    if callback.data == "donate_custom":
        await callback.message.answer(
            f"{Emoji.STAR} *Enter custom amount of Stars:*\n\n"
            f"Minimum: 10 Stars\n"
            f"Example: 250",
            parse_mode="Markdown"
        )
        await state.set_state(DonationState.waiting_amount)
        await callback.answer()
        return
    
    # Extract amount
    amount_str = callback.data.split("_")[1]
    try:
        stars = int(amount_str)
        await process_donation(callback, stars, state)
    except:
        await callback.answer("Invalid amount", show_alert=True)

@dp.message(DonationState.waiting_amount)
async def custom_amount(message: types.Message, state: FSMContext):
    """Process custom amount"""
    try:
        stars = int(message.text.strip())
        if stars < 10:
            await message.answer("Minimum amount: 10 Stars")
            return
        
        # Create fake callback
        class FakeCallback:
            def __init__(self):
                self.from_user = message.from_user
                self.message = message
        
        await process_donation(FakeCallback(), stars, state)
    except:
        await message.answer("Please enter a valid number (e.g., 250)")

async def process_donation(callback, stars: int, state: FSMContext):
    """Process donation"""
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    # Save data
    await state.update_data(stars=stars, user_id=user_id, username=username)
    await state.set_state(DonationState.processing)
    
    text = f"""
{Emoji.GEM} **PAYMENT REQUEST**

**Amount:** {stars} {Emoji.STAR}
**For:** @{username}
**Expires:** 24 hours

**How to pay:**
1. Tap *'Pay with Stars'*
2. Select amount: {stars} Stars
3. Complete payment
4. Return and tap *'Paid'*

**Rewards:**
• +{stars//10} XP
• Rank progression
• Exclusive benefits

*Secure payment via Telegram Stars*
    """
    
    keyboard = payment_menu(user_id, stars)
    
    try:
        if hasattr(callback, 'message'):
            await callback.message.edit_caption(
                caption=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await callback.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except:
        await callback.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    
    if hasattr(callback, 'answer'):
        await callback.answer()

@dp.callback_query(F.data.startswith("paid_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    """Confirm payment"""
    user_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    stars = data.get("stars", 0)
    username = data.get("username", "")
    
    # Update user
    rank, level = db.update_user(user_id, stars, username)
    
    # Generate achievement image
    img_buffer = MinimalistImage.generate_achievement(
        username=callback.from_user.username or callback.from_user.first_name,
        stars=stars,
        rank=rank
    )
    
    text = f"""
{Emoji.TROPHY} **PAYMENT CONFIRMED**

Thank you for your support!

**Details:**
{Emoji.STAR} Stars: {stars}
{Emoji.CROWN} New Rank: {rank}
{Emoji.FIRE} Level: {level}
{Emoji.CHART} Total: {db.get_user(user_id)['total_stars']} Stars

**Position:** #{db.get_user_position(user_id)}
**Community Total:** {db.data['total_stars']:,} Stars

*Welcome to the inner circle.*
    """
    
    try:
        await callback.message.answer_photo(
            photo=BufferedInputFile(img_buffer.getvalue(), filename="achievement.png"),
            caption=text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    except:
        await callback.message.edit_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "top")
async def leaderboard_handler(callback: types.CallbackQuery):
    """Leaderboard"""
    top_users = db.get_top_users(10)
    user_pos = db.get_user_position(callback.from_user.id)
    
    text = f"""
{Emoji.TROPHY} **LEADERBOARD**

**Community Stars:** {db.data['total_stars']:,}

**Top Contributors:**
"""
    
    for i, user in enumerate(top_users, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        username = user.get("username", "Anonymous")[:15]
        text += f"{medal} @{username}\n"
        text += f"   {user['total_stars']} {Emoji.STAR} | {user['rank']}\n\n"
    
    text += f"\n{Emoji.USER} **Your Position:** #{user_pos}"
    text += f"\n{Emoji.STAR} **Your Stars:** {db.get_user(callback.from_user.id)['total_stars']}"
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    """User profile"""
    user = db.get_user(callback.from_user.id)
    position = db.get_user_position(callback.from_user.id)
    
    text = f"""
{Emoji.USER} **PROFILE**

**Basic Info:**
ID: `{callback.from_user.id}`
Username: @{callback.from_user.username or 'Not set'}
Joined: {user['join_date'][:10]}

**Stats:**
{Emoji.CROWN} Rank: {user['rank']}
{Emoji.STAR} Total Stars: {user['total_stars']}
{Emoji.FIRE} Level: {user['level']} (XP: {user['xp']}/100)
{Emoji.TROPHY} Position: #{position}
{Emoji.CHART} Donations: {len(user['donations'])}

**Next Milestone:**
{100 - (user['total_stars'] % 100)} stars to level up

*Keep climbing.*
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "rewards")
async def rewards_handler(callback: types.CallbackQuery):
    """Rewards system"""
    user = db.get_user(callback.from_user.id)
    
    text = f"""
{Emoji.GIFT} **REWARDS SYSTEM**

**Your Stars:** {user['total_stars']} {Emoji.STAR}

**Available Rewards:**
• 10+ Stars → Exclusive emoji pack
• 100+ Stars → VIP status (30 days)
• 500+ Stars → Golden Banana NFT
• 1000+ Stars → Diamond membership
• 5000+ Stars → Co-founder status
• 10000+ Stars → Legendary role

**Unlocked:**
"""
    
    # Check unlocked rewards
    thresholds = [10, 100, 500, 1000, 5000, 10000]
    for threshold in thresholds:
        if user['total_stars'] >= threshold:
            text += f"✅ {threshold}+ Stars reward\n"
        else:
            needed = threshold - user['total_stars']
            text += f"🔒 {threshold} Stars ({needed} more needed)\n"
    
    text += "\n*Elegance through contribution.*"
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def stats_handler(callback: types.CallbackQuery):
    """Statistics"""
    text = f"""
{Emoji.CHART} **STATISTICS**

**Community:**
Total Users: {len(db.data['users'])}
Total Stars: {db.data['total_stars']:,}
Average per User: {db.data['total_stars'] // max(len(db.data['users']), 1):,}

**Your Stats:**
Stars: {db.get_user(callback.from_user.id)['total_stars']}
Rank: {db.get_user(callback.from_user.id)['rank']}
Position: #{db.get_user_position(callback.from_user.id)}

**Distribution:**
🌱 Seed: {len([u for u in db.data['users'].values() if u['total_stars'] < 100])}
🍌 Banana: {len([u for u in db.data['users'].values() if 100 <= u['total_stars'] < 1000])}
⭐ Star: {len([u for u in db.data['users'].values() if 1000 <= u['total_stars'] < 5000])}
👑 King: {len([u for u in db.data['users'].values() if u['total_stars'] >= 5000])}

*Data tells the story.*
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin")
async def admin_handler(callback: types.CallbackQuery):
    """Admin panel"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied", show_alert=True)
        return
    
    text = f"""
{Emoji.SETTINGS} **ADMIN PANEL**

**Overview:**
Users: {len(db.data['users'])}
Total Stars: {db.data['total_stars']:,}
Recent Activity: {len(db.data.get('events', []))}

**Quick Actions:**
• View detailed statistics
• Manage users
• Send announcements
• Backup database

*Admin privileges active.*
    """
    
    buttons = [
        [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 Announce", callback_data="admin_announce")],
        [InlineKeyboardButton(text=f"{Emoji.BACK} Back", callback_data="back")]
    ]
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@dp.callback_query(F.data == "back")
async def back_handler(callback: types.CallbackQuery, state: FSMContext):
    """Go back to main menu"""
    await state.clear()
    await start_command(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    """Cancel payment"""
    await state.clear()
    await callback.message.edit_caption(
        caption=f"{Emoji.BACK} *Payment cancelled*\n\nReturning to main menu...",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

# ============ ERROR HANDLER ============
@dp.errors()
async def error_handler(event):
    """Error handler"""
    logger.error(f"Error: {event.exception}")
    return True

# ============ MAIN ============
async def main():
    """Main function"""
    print(f"{Emoji.BANANA} BANANA NFT Bot starting...")
    
    try:
        me = await bot.get_me()
        print(f"Bot: @{me.username}")
        print(f"Stars system: Active")
        print(f"Database: {len(db.data['users'])} users")
        
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

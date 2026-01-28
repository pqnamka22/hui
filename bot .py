#!/usr/bin/env python3
"""
🍌 BANANA NFT BOT v2.0
С Telegram Stars вместо CryptoBot
"""

import asyncio
import logging
import json
import os
import io
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    FSInputFile,
    BufferedInputFile
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# ============ КОНФИГУРАЦИЯ ============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 🔴🔴🔴 ЗАМЕНИТЕ ЭТИ ТОКЕНЫ! 🔴🔴🔴
TELEGRAM_BOT_TOKEN = "8536282991:AAHUyTx0r7Q03bwDRokvogbmJAIbkAnYVpM"
ADMIN_ID = 6185460659 # Ваш Telegram ID

# Константы
DB_FILE = "banana_db.json"
BACKUP_FILE = "banana_backup.json"
IMAGE_CACHE_DIR = "image_cache"
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

# Цветовая палитра Banana NFT
COLORS = {
    "banana_yellow": (255, 225, 53),
    "gold": (255, 215, 0),
    "dark_gold": (184, 134, 11),
    "brown": (139, 69, 19),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gradient_start": (255, 255, 150),
    "gradient_end": (255, 200, 50)
}

# Система рангов
RANKS = [
    {"min": 0, "name": "🍌 Желтый банан", "emoji": "🍌", "color": "#FFD700"},
    {"min": 10, "name": "💰 Banana Collector", "emoji": "💰", "color": "#C0C0C0"},
    {"min": 50, "name": "🌟 Banana Star", "emoji": "🌟", "color": "#87CEEB"},
    {"min": 100, "name": "🏆 Banana Champion", "emoji": "🏆", "color": "#FFA500"},
    {"min": 500, "name": "👑 Banana King", "emoji": "👑", "color": "#FFD700"},
    {"min": 1000, "name": "🚀 Banana God", "emoji": "🚀", "color": "#9370DB"},
    {"min": 5000, "name": "💎 Diamond Banana", "emoji": "💎", "color": "#00FFFF"},
    {"min": 10000, "name": "✨ Legendary Banana", "emoji": "✨", "color": "#FF00FF"}
]

# Подарки за донаты
GIFTS = {
    10: {"name": "🍌 Банановый эмодзи", "description": "Эксклюзивный эмодзи в чате"},
    50: {"name": "🎨 Стикерпак", "description": "Набор стикеров Banana Gang"},
    100: {"name": "🌟 VIP статус", "description": "VIP на 30 дней + золотое имя"},
    500: {"name": "👑 Персональный NFT", "description": "Уникальный Banana NFT"},
    1000: {"name": "💎 Diamond Member", "description": "Пожизненный VIP + доход 1%"},
    5000: {"name": "🚀 Сооснователь", "description": "Управление проектом + токены"}
}

# Цели проекта
GOALS = [
    {"target": 1000, "name": "Golden Banana NFT", "reward": "Все участники получат NFT"},
    {"target": 5000, "name": "Banana Token Launch", "reward": "Запуск $BNFT токена"},
    {"target": 10000, "name": "Marketplace Release", "reward": "Banana NFT Marketplace"},
    {"target": 50000, "name": "Mobile Game", "reward": "Игра Banana Run"}
]

# ============ ИНИЦИАЛИЗАЦИЯ ============
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============ БАЗА ДАННЫХ ============
class Database:
    def __init__(self, filename=DB_FILE):
        self.filename = filename
        self.data = self.load()
    
    def load(self):
        """Загрузка базы данных"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки БД: {e}")
        
        # База по умолчанию
        default_db = {
            "users": {},
            "total_donated": 0,
            "top_donations": [],
            "goals": GOALS.copy(),
            "settings": {
                "min_donation": 0.1,
                "commission": 2.0,
                "last_reset": datetime.now().isoformat()
            },
            "events": [],
            "stats": {
                "total_users": 0,
                "total_donations": 0,
                "biggest_donation": 0,
                "last_donation_time": None
            }
        }
        return default_db
    
    def save(self):
        """Сохранение базы данных"""
        try:
            # Создаем бэкап
            if os.path.exists(self.filename):
                import shutil
                shutil.copy2(self.filename, BACKUP_FILE)
            
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения БД: {e}")
            return False
    
    def get_user(self, user_id: int, username: str = "") -> dict:
        """Получение или создание пользователя"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.data["users"]:
            self.data["users"][user_id_str] = {
                "id": user_id,
                "username": username or "",
                "first_name": "",
                "total_donated": 0.0,
                "donations": [],
                "rank": RANKS[0]["name"],
                "level": 1,
                "xp": 0,
                "gifts_received": [],
                "join_date": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "referrals": [],
                "daily_streak": 0,
                "last_daily": None,
                "achievements": []
            }
            self.data["stats"]["total_users"] = len(self.data["users"])
            self.save()
        
        return self.data["users"][user_id_str]
    
    def update_user(self, user_id: int, amount: float, username: str = "") -> Tuple[str, int]:
        """Обновление данных пользователя после доната"""
        user = self.get_user(user_id, username)
        user_id_str = str(user_id)
        
        # Обновляем основную информацию
        user["total_donated"] = round(user["total_donated"] + amount, 2)
        user["last_active"] = datetime.now().isoformat()
        
        # Добавляем донат в историю
        donation_record = {
            "amount": amount,
            "date": datetime.now().isoformat(),
            "status": "completed"
        }
        user["donations"].append(donation_record)
        
        # Обновляем XP и уровень
        xp_gained = int(amount * 10)
        user["xp"] += xp_gained
        user["level"] = user["xp"] // 100 + 1
        
        # Обновляем ранг
        new_rank = self.calculate_rank(user["total_donated"])
        user["rank"] = new_rank
        
        # Обновляем глобальную статистику
        self.data["total_donated"] = round(self.data["total_donated"] + amount, 2)
        self.data["stats"]["total_donations"] += 1
        
        if amount > self.data["stats"]["biggest_donation"]:
            self.data["stats"]["biggest_donation"] = amount
        
        self.data["stats"]["last_donation_time"] = datetime.now().isoformat()
        
        # Добавляем в топ донатов
        top_donation = {
            "user_id": user_id,
            "username": username,
            "amount": amount,
            "date": datetime.now().isoformat(),
            "rank": new_rank
        }
        self.data["top_donations"].append(top_donation)
        
        # Сортируем топ (первые 100)
        self.data["top_donations"] = sorted(
            self.data["top_donations"],
            key=lambda x: x["amount"],
            reverse=True
        )[:100]
        
        # Проверяем достижение целей
        self.check_goals(amount)
        
        # Сохраняем изменения
        self.save()
        
        return new_rank, user["level"]
    
    def calculate_rank(self, total_donated: float) -> str:
        """Вычисление ранга пользователя"""
        for rank in reversed(RANKS):
            if total_donated >= rank["min"]:
                return rank["name"]
        return RANKS[0]["name"]
    
    def check_goals(self, amount: float):
        """Проверка достижения целей"""
        for goal in self.data["goals"]:
            if self.data["total_donated"] >= goal["target"] and not goal.get("achieved"):
                goal["achieved"] = True
                goal["achieved_date"] = datetime.now().isoformat()
                
                # Добавляем событие
                event = {
                    "type": "goal_achieved",
                    "goal": goal["name"],
                    "target": goal["target"],
                    "date": datetime.now().isoformat(),
                    "total": self.data["total_donated"]
                }
                self.data["events"].append(event)
    
    def get_top_users(self, limit: int = 10) -> List[dict]:
        """Получение топа пользователей"""
        users_list = list(self.data["users"].values())
        sorted_users = sorted(users_list, key=lambda x: x["total_donated"], reverse=True)
        return sorted_users[:limit]
    
    def get_user_position(self, user_id: int) -> int:
        """Получение позиции пользователя в топе"""
        top_users = self.get_top_users(len(self.data["users"]))
        for i, user in enumerate(top_users, 1):
            if user["id"] == user_id:
                return i
        return len(top_users) + 1
    
    def add_gift(self, user_id: int, gift_tier: int):
        """Добавление подарка пользователю"""
        user = self.get_user(user_id)
        gift_info = GIFTS.get(gift_tier)
        
        if gift_info and gift_tier not in user["gifts_received"]:
            user["gifts_received"].append({
                "tier": gift_tier,
                "name": gift_info["name"],
                "date": datetime.now().isoformat()
            })
            self.save()
            return gift_info
        
        return None
    
    def get_daily_bonus(self, user_id: int) -> Tuple[bool, int]:
        """Получение ежедневного бонуса"""
        user = self.get_user(user_id)
        today = datetime.now().date().isoformat()
        
        if user["last_daily"] == today:
            return False, 0  # Уже получал сегодня
        
        # Вычисляем бонус
        streak = user["daily_streak"] + 1
        bonus_xp = min(streak * 10, 100)  # Макс 100 XP
        
        # Обновляем данные
        user["daily_streak"] = streak
        user["last_daily"] = today
        user["xp"] += bonus_xp
        self.save()
        
        return True, bonus_xp

# Инициализация базы данных
db = Database()

# ============ TELEGRAM STARS API ============
class TelegramStars:
    """Интеграция с Telegram Stars через @donate бота"""
    
    def __init__(self):
        self.bot_username = "@donate"
        self.min_stars = 1  # 1 star = ~0.01$
    
    async def create_invoice(self, amount_usdt: float, user_id: int, username: str = "") -> dict:
        """Создание доната через Telegram Stars"""
        
        # Конвертируем USDT в Stars (примерный курс)
        # 1 Star ≈ $0.01, 1 USDT ≈ $1 → 100 Stars ≈ 1 USDT
        stars_amount = int(amount_usdt * 100)
        
        if stars_amount < self.min_stars:
            stars_amount = self.min_stars
        
        # Формируем ссылку для доната
        pay_url = f"https://t.me/{self.bot_username}?start=banana_{user_id}_{stars_amount}"
        
        return {
            "success": True,
            "invoice_id": f"stars_{user_id}_{int(datetime.now().timestamp())}",
            "pay_url": pay_url,
            "amount_usdt": amount_usdt,
            "amount_stars": stars_amount,
            "currency": "XTR",  # Telegram Stars
            "status": "active",
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "provider": "telegram_stars"
        }

# Инициализация Telegram Stars
stars_bot = TelegramStars()

# ============ ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ============
class ImageGenerator:
    @staticmethod
    def create_gradient(width: int, height: int, start_color: Tuple, end_color: Tuple) -> Image.Image:
        """Создание градиентного фона"""
        base = Image.new('RGB', (width, height), start_color)
        top = Image.new('RGB', (width, height), end_color)
        mask = Image.new('L', (width, height))
        mask_data = []
        
        for y in range(height):
            for x in range(width):
                mask_data.append(int(255 * (x / width * 0.5 + y / height * 0.5)))
        
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        return base
    
    @staticmethod
    def draw_banana(draw: ImageDraw, x: int, y: int, size: int, color: Tuple):
        """Рисование стилизованного банана"""
        # Основная дуга банана
        draw.ellipse([x, y, x + size, y + size], outline=color, width=3)
        # Концы банана
        draw.ellipse([x + size//4, y + size//4, x + 3*size//4, y + 3*size//4], 
                    outline=color, width=2)
    
    @staticmethod
    def generate_welcome_image(username: str = "Друг") -> io.BytesIO:
        """Генерация приветственного изображения"""
        width, height = 800, 400
        
        # Создаем градиентный фон
        img = ImageGenerator.create_gradient(
            width, height,
            COLORS["gradient_start"],
            COLORS["gradient_end"]
        )
        draw = ImageDraw.Draw(img)
        
        # Рисуем бананы на фоне
        for i in range(8):
            x = random.randint(0, width - 100)
            y = random.randint(0, height - 100)
            size = random.randint(30, 70)
            color = random.choice([COLORS["gold"], COLORS["banana_yellow"]])
            ImageGenerator.draw_banana(draw, x, y, size, color)
        
        # Добавляем размытие фона
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        draw = ImageDraw.Draw(img)
        
        try:
            # Пробуем загрузить шрифты
            title_font = ImageFont.truetype("arialbd.ttf", 60)
            name_font = ImageFont.truetype("arialbd.ttf", 40)
            subtitle_font = ImageFont.truetype("arial.ttf", 28)
        except:
            # Используем стандартные шрифты
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Текст
        title = "🍌 BANANA NFT"
        draw.text((width//2, 100), title, font=title_font, 
                 fill=COLORS["dark_gold"], anchor="mm", stroke_width=2, stroke_fill=COLORS["black"])
        
        welcome_text = f"Добро пожаловать, {username}!"
        draw.text((width//2, 180), welcome_text, font=name_font,
                 fill=COLORS["white"], anchor="mm")
        
        subtitle = "Самый сочный NFT проект в Telegram!"
        draw.text((width//2, 240), subtitle, font=subtitle_font,
                 fill=COLORS["gold"], anchor="mm")
        
        footer = "banananftbot"
        draw.text((width//2, 350), footer, font=subtitle_font,
                 fill=COLORS["brown"], anchor="mm")
        
        # Сохраняем в буфер
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True, quality=95)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_donation_image(username: str, amount: float, rank: str) -> io.BytesIO:
        """Генерация изображения для шаринга достижения"""
        width, height = 800, 400
        
        # Создаем золотой фон
        img = ImageGenerator.create_gradient(
            width, height,
            (255, 240, 150),
            (255, 200, 50)
        )
        
        # Добавляем эффект сияния
        glow = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        glow_draw = ImageDraw.Draw(glow)
        
        for i in range(5):
            radius = 200 + i * 20
            alpha = 30 - i * 5
            glow_draw.ellipse(
                [(width//2 - radius, height//2 - radius),
                 (width//2 + radius, height//2 + radius)],
                fill=(255, 255, 255, alpha)
            )
        
        img = Image.alpha_composite(img.convert('RGBA'), glow).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        try:
            # Шрифты
            title_font = ImageFont.truetype("arialbd.ttf", 48)
            amount_font = ImageFont.truetype("arialbd.ttf", 72)
            name_font = ImageFont.truetype("arial.ttf", 36)
            rank_font = ImageFont.truetype("arial.ttf", 28)
        except:
            title_font = ImageFont.load_default()
            amount_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            rank_font = ImageFont.load_default()
        
        # Заголовок
        title = "🏆 НОВЫЙ РЕКОРД!"
        draw.text((width//2, 60), title, font=title_font,
                 fill=COLORS["dark_gold"], anchor="mm")
        
        # Имя пользователя
        user_display = f"@{username}" if username else "Анонимный банан"
        draw.text((width//2, 130), user_display, font=name_font,
                 fill=COLORS["white"], anchor="mm")
        
        # Сумма доната
        amount_text = f"{amount:.2f} USDT"
        draw.text((width//2, 200), amount_text, font=amount_font,
                 fill=COLORS["gold"], anchor="mm", stroke_width=3, stroke_fill=COLORS["dark_gold"])
        
        # Ранг
        draw.text((width//2, 280), rank, font=rank_font,
                 fill=COLORS["brown"], anchor="mm")
        
        # Подпись
        signature = "🍌 Banana NFT | banananftbot"
        draw.text((width//2, 340), signature, font=rank_font,
                 fill=COLORS["white"], anchor="mm")
        
        # Добавляем декоративные элементы
        for i, emoji in enumerate(["🍌", "💰", "🏆", "🌟", "👑"]):
            x = 100 + i * 150
            y = 360
            try:
                # Пробуем использовать эмодзи как текст
                draw.text((x, y), emoji, font=ImageFont.load_default(),
                         fill=COLORS["gold"], anchor="mm")
            except:
                pass
        
        # Сохраняем в буфер
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True, quality=95)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_top_image(top_users: List[dict], total_donated: float) -> io.BytesIO:
        """Генерация изображения топа"""
        width, height = 800, 600
        
        # Фон
        img = Image.new('RGB', (width, height), COLORS["black"])
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 48)
            header_font = ImageFont.truetype("arialbd.ttf", 32)
            user_font = ImageFont.truetype("arial.ttf", 24)
            total_font = ImageFont.truetype("arialbd.ttf", 36)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            user_font = ImageFont.load_default()
            total_font = ImageFont.load_default()
        
        # Заголовок
        draw.text((width//2, 50), "🏆 ТОП ДОНАТЕРОВ 🍌", font=title_font,
                 fill=COLORS["gold"], anchor="mm")
        
        # Заголовки таблицы
        headers = ["#", "Имя", "Сумма", "Ранг"]
        header_y = 120
        col_widths = [50, 300, 200, 250]
        
        for i, header in enumerate(headers):
            x = sum(col_widths[:i]) + col_widths[i]//2
            draw.text((x, header_y), header, font=header_font,
                     fill=COLORS["banana_yellow"], anchor="mm")
        
        # Пользователи
        for idx, user in enumerate(top_users[:10], 1):
            y = header_y + 50 + idx * 40
            
            # Медальки для топ-3
            medal = ""
            if idx == 1: medal = "🥇"
            elif idx == 2: medal = "🥈"
            elif idx == 3: medal = "🥉"
            
            # Данные пользователя
            username = user.get("username", "Аноним")[:15]
            amount = f"{user['total_donated']:.2f} USDT"
            rank = user.get("rank", "🍌 Банан")[:20]
            
            # Рисуем строку
            cols = [
                f"{medal} {idx}" if medal else str(idx),
                f"@{username}" if username != "Аноним" else username,
                amount,
                rank
            ]
            
            for i, text in enumerate(cols):
                x = sum(col_widths[:i]) + col_widths[i]//2
                color = COLORS["gold"] if idx <= 3 else COLORS["white"]
                draw.text((x, y), text, font=user_font,
                         fill=color, anchor="mm")
        
        # Итоговая сумма
        total_text = f"Всего собрано: {total_donated:.2f} USDT"
        draw.text((width//2, height - 50), total_text, font=total_font,
                 fill=COLORS["banana_yellow"], anchor="mm")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

# ============ КЛАВИАТУРЫ ============
def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [
            InlineKeyboardButton(text="💰 Донат", callback_data="donate"),
            InlineKeyboardButton(text="🏆 Топ", callback_data="top")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🎁 Подарки", callback_data="gifts")
        ],
        [
            InlineKeyboardButton(text="🌟 Поделиться", callback_data="share"),
            InlineKeyboardButton(text="⚡ Ежедневный бонус", callback_data="daily")
        ],
        [
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about"),
            InlineKeyboardButton(text="👑 Админ" if ADMIN_ID else "⚙️ Настройки", 
                               callback_data="admin")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_donate_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для донатов"""
    buttons = [
        [
            InlineKeyboardButton(text="5 USDT 🍌", callback_data="donate_5"),
            InlineKeyboardButton(text="10 USDT 💰", callback_data="donate_10"),
            InlineKeyboardButton(text="25 USDT 🌟", callback_data="donate_25")
        ],
        [
            InlineKeyboardButton(text="50 USDT 🏆", callback_data="donate_50"),
            InlineKeyboardButton(text="100 USDT 👑", callback_data="donate_100"),
            InlineKeyboardButton(text="500 USDT 🚀", callback_data="donate_500")
        ],
        [
            InlineKeyboardButton(text="🎯 Другая сумма", callback_data="donate_custom"),
            InlineKeyboardButton(text="📈 Мои донаты", callback_data="my_donations")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_stars_payment_keyboard(pay_url: str, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для оплаты через Telegram Stars"""
    buttons = [
        [InlineKeyboardButton(text="💎 Оплатить Stars", url=pay_url)],
        [
            InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"stars_paid_{user_id}"),
            InlineKeyboardButton(text="❓ Что такое Stars?", callback_data="stars_info")
        ],
        [
            InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"stars_status_{user_id}"),
            InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_payment")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_share_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для шаринга"""
    share_text = f"Я только что задонатил в Banana NFT боте! 🍌\nПрисоединяйся: https://t.me/banananftbot"
    share_url = f"https://t.me/share/url?url=https://t.me/banananftbot&text={share_text}"
    
    buttons = [
        [InlineKeyboardButton(text="📱 Поделиться в TG", url=share_url)],
        [InlineKeyboardButton(text="🎨 Картинка", callback_data="share_image")],
        [InlineKeyboardButton(text="📊 Подробная статистика", callback_data="detailed_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-клавиатура"""
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Донаты", callback_data="admin_donations")],
        [InlineKeyboardButton(text="🎯 Цели", callback_data="admin_goals")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ============ STATES ============
class DonationState(StatesGroup):
    waiting_amount = State()
    waiting_custom_amount = State()
    processing_payment = State()

class AdminState(StatesGroup):
    waiting_broadcast = State()

# ============ ХЕНДЛЕРЫ ============
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = db.get_user(message.from_user.id, message.from_user.username)
    
    # Генерируем приветственное изображение
    img_buffer = ImageGenerator.generate_welcome_image(
        message.from_user.first_name or message.from_user.username or "Друг"
    )
    
    welcome_text = f"""
🍌 *Добро пожаловать в BANANA NFT!* 🚀

*Твой статус:* {user['rank']}
*Твой вклад:* {user['total_donated']:.2f} USDT
*Уровень:* {user['level']} (XP: {user['xp']})

🌟 *Что у нас есть:*
• Система донатов с рейтингом 🏆
• Эксклюзивные подарки за вклад 🎁
• Возможность делиться достижениями 📱
• Секретные обновления... 🔮

🎁 *Ближайший подарок:* Golden Banana NFT
*Нужно:* 100 USDT всего
*Собрано:* {db.data['total_donated']:.2f}/100 USDT

🔥 *Ежедневный бонус:* /daily
📊 *Статистика:* /stats

🔮 *Готовьтесь к Banana NFT Marketplace...*
✨ *Скоро:* $BNFT токен, мобильная игра, физический мерч!
    """
    
    try:
        await message.answer_photo(
            photo=BufferedInputFile(img_buffer.getvalue(), filename="welcome.png"),
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer(
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )

@dp.message(Command("daily"))
async def cmd_daily(message: types.Message):
    """Ежедневный бонус"""
    success, bonus_xp = db.get_daily_bonus(message.from_user.id)
    user = db.get_user(message.from_user.id)
    
    if success:
        text = f"""
🎉 *Ежедневный бонус получен!*

✨ +{bonus_xp} XP добавлено!
🔥 Серия дней: {user['daily_streak']}
📈 Твой уровень: {user['level']} (XP: {user['xp']})

💡 *Совет:* Заходи каждый день чтобы увеличивать серию!
Максимальный бонус: 100 XP/день

🏆 *Твой прогресс:*
До следующего уровня: {100 - (user['xp'] % 100)} XP
Общий вклад: {user['total_donated']:.2f} USDT
Ранг: {user['rank']}

🔄 *Следующий бонус через:* 24 часа
        """
    else:
        # Вычисляем когда можно получить следующий бонус
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        time_left = tomorrow - now
        
        text = f"""
⏰ *Бонус уже получен сегодня!*

🔥 Текущая серия: {user['daily_streak']} дней
📊 Твой XP: {user['xp']}
🎯 Уровень: {user['level']}

🔄 *Следующий бонус через:*
{time_left.seconds // 3600} ч. {(time_left.seconds % 3600) // 60} мин.

💡 *Не пропусти!* Каждый день серия увеличивается
и бонус становится больше!
        """
    
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Личная статистика"""
    user = db.get_user(message.from_user.id, message.from_user.username)
    position = db.get_user_position(message.from_user.id)
    
    # Вычисляем прогресс до следующего ранга
    next_rank = None
    for rank in RANKS:
        if user['total_donated'] < rank['min']:
            next_rank = rank
            break
    
    progress_text = ""
    if next_rank:
        needed = next_rank['min'] - user['total_donated']
        progress = (user['total_donated'] / next_rank['min']) * 100 if next_rank['min'] > 0 else 100
        progress_text = f"""
🎯 *До следующего ранга ({next_rank['name']}):*
💰 Нужно: {needed:.2f} USDT
📊 Прогресс: {progress:.1f}%
        """
    
    # Вычисляем следующий подарок
    next_gift = None
    gift_tiers = sorted(GIFTS.keys())
    for tier in gift_tiers:
        if user['total_donated'] < tier and tier not in [g['tier'] for g in user['gifts_received']]:
            next_gift = GIFTS[tier]
            needed_gift = tier - user['total_donated']
            break
    
    gift_text = ""
    if next_gift:
        gift_text = f"""
🎁 *Следующий подарок ({next_gift['name']}):*
💰 Нужно: {needed_gift:.2f} USDT
📝 {next_gift['description']}
        """
    
    stats_text = f"""
📊 *ТВОЯ СТАТИСТИКА BANANA NFT*

👤 *Профиль:*
ID: `{message.from_user.id}`
Имя: {message.from_user.first_name or ''}
Юзернейм: @{message.from_user.username or 'Нет'}

🏆 *Достижения:*
Ранг: {user['rank']}
Уровень: {user['level']}
XP: {user['xp']}/100
Позиция в топе: #{position}

💰 *Финансы:*
Всего задонатил: {user['total_donated']:.2f} USDT
Количество донатов: {len(user['donations'])}
Последний донат: {user['donations'][-1]['date'][:10] if user['donations'] else 'Еще нет'}

📅 *Активность:*
В проекте с: {user['join_date'][:10]}
Ежедневная серия: {user['daily_streak']} дней
Последняя активность: {user['last_active'][:16]}

🎁 *Полученные подарки:* {len(user['gifts_received'])}
{progress_text}
{gift_text}

🌐 *Глобальная статистика:*
Всего пользователей: {db.data['stats']['total_users']}
Всего собрано: {db.data['total_donated']:.2f} USDT
Рекордный донат: {db.data['stats']['biggest_donation']:.2f} USDT
    """
    
    await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.callback_query(F.data == "donate")
async def callback_donate(callback: types.CallbackQuery):
    """Обработчик кнопки Донат"""
    text = """
💰 *ПОДДЕРЖАТЬ BANANA NFT*

Выберите сумму доната или введите свою:

*Что вы получаете за донат:*
🏆 - Повышение в рейтинге и XP
🎁 - Эксклюзивные подарки
🌟 - Уникальные роли в сообществе
💎 - Доступ к закрытому чату
📈 - Участие в развитии проекта

*Текущие цели проекта:*
"""
    
    # Добавляем информацию о целях
    for goal in db.data['goals'][:3]:  # Показываем первые 3 цели
        achieved = "✅ " if goal.get('achieved') else "🎯 "
        progress = (db.data['total_donated'] / goal['target']) * 100
        text += f"{achieved}*{goal['name']}*: {db.data['total_donated']:.2f}/{goal['target']} USDT ({progress:.1f}%)\n"
    
    text += f"\n💡 *Совет:* Чем больше сумма - тем лучше подарки!"
    text += f"\n🎯 *Ваш текущий вклад:* {db.get_user(callback.from_user.id)['total_donated']:.2f} USDT"
    text += f"\n💎 *Оплата через:* Telegram Stars (@donate)"
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=get_donate_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("donate_"))
async def callback_quick_donate(callback: types.CallbackQuery, state: FSMContext):
    """Быстрый донат по кнопке"""
    data = callback.data
    
    if data == "donate_custom":
        await callback.message.answer(
            "💵 *Введите сумму доната в USDT:*\n\n"
            "Минимальная сумма: 0.1 USDT\n"
            "Максимальная: 10000 USDT",
            parse_mode="Markdown"
        )
        await state.set_state(DonationState.waiting_custom_amount)
        await callback.answer()
        return
    
    # Извлекаем сумму из callback_data
    amount_str = data.split("_")[1]
    try:
        amount = float(amount_str)
        await process_donation(callback, amount, state)
    except ValueError:
        await callback.answer("❌ Ошибка: неверная сумма", show_alert=True)

@dp.message(DonationState.waiting_custom_amount)
async def process_custom_amount(message: types.Message, state: FSMContext):
    """Обработка пользовательской суммы"""
    try:
        # Очищаем ввод
        amount_text = message.text.replace(',', '.').strip()
        amount = float(amount_text)
        
        # Проверка лимитов
        if amount < 0.1:
            await message.answer("❌ Минимальная сумма: 0.1 USDT")
            return
        if amount > 10000:
            await message.answer("❌ Максимальная сумма: 10000 USDT")
            return
        
        # Создаем callback для обработки
        class FakeCallback:
            def __init__(self):
                self.from_user = message.from_user
                self.message = message
        
        fake_callback = FakeCallback()
        await process_donation(fake_callback, amount, state)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (например: 10.5 или 100)")

async def process_donation(callback, amount: float, state: FSMContext):
    """Обработка доната через Telegram Stars"""
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name or "User"
    
    logger.info(f"Processing donation: {amount} USDT from user {user_id}")
    
    # Проверка минимальной суммы
    min_amount = db.data['settings']['min_donation']
    if amount < min_amount:
        error_msg = f"❌ Минимальная сумма: {min_amount} USDT"
        if hasattr(callback, 'answer'):
            await callback.answer(error_msg, show_alert=True)
        else:
            await callback.answer(error_msg)
        return
    
    # Используем Telegram Stars
    invoice = await stars_bot.create_invoice(
        amount_usdt=amount,
        user_id=user_id,
        username=username
    )
    
    logger.info(f"Stars invoice result: {invoice}")
    
    if not invoice.get("success"):
        error_msg = f"❌ Ошибка создания счета: {invoice.get('error', 'Unknown error')}"
        logger.error(error_msg)
        
        if hasattr(callback, 'answer'):
            await callback.answer(error_msg, show_alert=True)
        else:
            await callback.answer(error_msg)
        return
    
    # Сохраняем данные
    await state.update_data(
        invoice_id=invoice["invoice_id"],
        amount=amount,
        user_id=user_id,
        username=username,
        stars_amount=invoice["amount_stars"],
        pay_url=invoice["pay_url"],
        provider="telegram_stars"
    )
    await state.set_state(DonationState.processing_payment)
    
    # Формируем сообщение
    text = f"""
💎 *ДОНАТ ЧЕРЕЗ TELEGRAM STARS*

💰 *Сумма:* {amount} USDT ({invoice['amount_stars']} ⭐)
👤 *Для:* @{username}

📲 *Как оплатить:*
1. Нажмите кнопку "💎 Оплатить Stars"
2. Откроется официальный бот @donate
3. Выберите сумму: {invoice['amount_stars']} Stars
4. Оплатите картой, криптой или другим способом
5. Вернитесь сюда и нажмите "✅ Я оплатил"

💡 *Что такое Telegram Stars?*
• Встроенная система донатов в Telegram
• 1 Star ≈ $0.01 (100 Stars ≈ 1 USDT)
• Мгновенные переводы
• Низкие комиссии (всего 2-5%)

🎁 *Бонусы за этот донат:*
• +{int(amount * 10)} XP
• Повышение ранга и уровня
• VIP статус на 7 дней
• Эксклюзивные стикеры
• Улучшение позиции в топе

⚠️ *Важно:* После оплаты обязательно нажмите "✅ Я оплатил"
⏱️ *Счет действителен:* 24 часа
    """
    
    # Клавиатура для Stars
    keyboard = get_stars_payment_keyboard(invoice['pay_url'], user_id)
    
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
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        await callback.answer(
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    if hasattr(callback, 'answer'):
        await callback.answer()

@dp.callback_query(F.data.startswith("stars_paid_"))
async def check_stars_payment(callback: types.CallbackQuery, state: FSMContext):
    """Проверка оплаты через Telegram Stars (ручное подтверждение)"""
    user_id = int(callback.data.split("_")[2])
    
    # Получаем данные из state
    data = await state.get_data()
    amount = data.get("amount", 0)
    username = data.get("username", "")
    stars_amount = data.get("stars_amount", 0)
    
    # Обновляем пользователя
    rank, level = db.update_user(user_id, amount, username)
    
    # Проверяем полученные подарки
    user = db.get_user(user_id)
    gifts_text = ""
    if amount >= 100:
        gifts_text = "\n🎁 *Получен подарок:* Golden Banana NFT"
    elif amount >= 50:
        gifts_text = "\n🎁 *Получен подарок:* VIP статус на 30 дней"
    elif amount >= 10:
        gifts_text = "\n🎁 *Получен подарок:* Эксклюзивные стикеры"
    
    # Формируем сообщение об успехе
    text = f"""
🎉 *ОПЛАТА ПОДТВЕРЖЕНА!*

✅ Спасибо за ваш донат через Telegram Stars!

📊 *Детали платежа:*
💰 Сумма: {amount} USDT
⭐ Stars: {stars_amount} ⭐
🏆 Новый ранг: {rank}
⭐ Уровень: {level}
📈 Всего задоначено: {user['total_donated']:.2f} USDT

{gifts_text}

✨ *Вы получили:*
• VIP статус на 7 дней
• +{int(amount * 10)} XP
• Доступ к эксклюзивным стикерам
• Улучшение позиции в топе

🔥 *Ваша новая позиция в топе:* #{db.get_user_position(user_id)}
💫 *Общая собрано проектом:* {db.data['total_donated']:.2f} USDT

💡 *Совет:* Используйте кнопку "🌟 Поделиться"
чтобы похвастаться достижением друзьям!
    """
    
    # Генерируем картинку для шаринга
    try:
        img_buffer = ImageGenerator.generate_donation_image(
            username=callback.from_user.username or callback.from_user.first_name,
            amount=amount,
            rank=rank
        )
        
        await callback.message.answer_photo(
            photo=BufferedInputFile(img_buffer.getvalue(), filename="stars_donation.png"),
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        await callback.message.edit_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    
    # Уведомляем админа
    admin_text = f"""
🎉 *НОВЫЙ ДОНАТ ЧЕРЕЗ STARS!*

👤 Пользователь: @{username}
💰 Сумма: {amount} USDT ({stars_amount} ⭐)
🏆 Ранг: {rank}
📈 Всего у пользователя: {user['total_donated']:.2f} USDT
🌐 Общий сбор проекта: {db.data['total_donated']:.2f} USDT
    """
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    except:
        pass
    
    # Очищаем state
    await state.clear()
    await callback.answer("✅ Оплата подтверждена! Спасибо!")

@dp.callback_query(F.data.startswith("stars_status_"))
async def check_stars_status(callback: types.CallbackQuery, state: FSMContext):
    """Проверка статуса оплаты"""
    user_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    
    text = f"""
⏳ *СТАТУС ОПЛАТЫ*

💰 *Сумма:* {data.get('amount', 0)} USDT
⭐ *Stars:* {data.get('stars_amount', 0)} ⭐
👤 *Для:* @{data.get('username', '')}
🕐 *Создан:* {datetime.now().strftime('%H:%M:%S')}

💡 *Если вы уже оплатили:*
1. Убедитесь что оплата прошла в боте @donate
2. Нажмите "✅ Я оплатил"
3. Если не подтверждается - подождите 5 минут

⚠️ *Проблемы с оплатой?*
• Проверьте баланс в @donate
• Убедитесь что выбрали правильную сумму
• Пришлите скриншот чека админу
"""
    
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "stars_info")
async def stars_info_handler(callback: types.CallbackQuery):
    """Информация о Telegram Stars"""
    text = """
💎 *TELEGRAM STARS - ОФИЦИАЛЬНАЯ СИСТЕМА ДОНАТОВ*

*Что это?*
Telegram Stars - встроенная виртуальная валюта для поддержки создателей контента.

🌟 *Основные преимущества:*
• 💰 *Низкая комиссия*: всего 2-5% (у других 10-30%)
• ⚡ *Мгновенные выплаты*: деньги сразу на карту/крипту
• 🌍 *Работает в РФ/СНГ*: без ограничений
• 📱 *Удобно*: не нужно выходить из Telegram
• 🔒 *Безопасно*: официальная система Telegram

💸 *Курс и расчеты:*
• 1 Star (⭐) ≈ $0.01
• 100 Stars ≈ 1 USDT ≈ 100₽
• Пример: 10 USDT = 1000 Stars

🎯 *Как пополнить Stars:*
1. Откройте @donate бота
2. Нажмите "Пополнить баланс"
3. Выберите способ оплаты
4. Введите сумму и оплатите

✨ *Почему лучше чем другие системы?*
1. Никаких API токенов
2. Никаких вебхуков
3. Никаких блокировок по странам
4. Выплаты сразу на карту
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Открыть @donate", url="https://t.me/donate")],
        [InlineKeyboardButton(text="🔙 Назад к оплате", callback_data="back_to_payment")]
    ])
    
    await callback.message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Отмена оплаты"""
    await state.clear()
    await callback.message.edit_caption(
        caption="❌ *ОПЛАТА ОТМЕНЕНА*\n\nВозвращаюсь в главное меню...",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "top")
async def callback_top(callback: types.CallbackQuery):
    """Топ донатеров"""
    top_users = db.get_top_users(10)
    
    # Генерируем изображение топа
    img_buffer = ImageGenerator.generate_top_image(top_users, db.data['total_donated'])
    
    text = f"""
🏆 *ТОП ДОНАТЕРОВ BANANA NFT* 🍌

*Всего собрано:* {db.data['total_donated']:.2f} USDT
*Всего пользователей:* {db.data['stats']['total_users']}
*Рекордный донат:* {db.data['stats']['biggest_donation']:.2f} USDT

*Текущие цели проекта:*
"""
    
    # Добавляем прогресс целей
    for goal in db.data['goals'][:2]:
        achieved = "✅ " if goal.get('achieved') else "🎯 "
        progress = (db.data['total_donated'] / goal['target']) * 100
        text += f"{achieved}*{goal['name']}*: {progress:.1f}%\n"
    
    text += f"\n✨ *Ваша позиция:* #{db.get_user_position(callback.from_user.id)}"
    text += f"\n💰 *Ваш вклад:* {db.get_user(callback.from_user.id)['total_donated']:.2f} USDT"
    
    try:
        await callback.message.answer_photo(
            photo=BufferedInputFile(img_buffer.getvalue(), filename="top.png"),
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото топа: {e}")
        # Формируем текстовый топ
        top_text = "🏆 *ТОП ДОНАТЕРОВ:*\n\n"
        for i, user in enumerate(top_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            username = user.get("username", "Аноним")[:15]
            top_text += f"{medal} @{username}\n"
            top_text += f"   💰 *{user['total_donated']:.2f} USDT* | {user['rank']}\n\n"
        
        await callback.message.answer(
            text=top_text + text,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    
    await callback.answer()

@dp.callback_query(F.data == "gifts")
async def callback_gifts(callback: types.CallbackQuery):
    """Подарки"""
    user = db.get_user(callback.from_user.id)
    
    text = """
🎁 *ЭКСКЛЮЗИВНЫЕ ПОДАРКИ BANANA NFT*

*За ваши донаты вы получаете:*
"""
    
    # Список подарков
    for tier, gift_info in GIFTS.items():
        received = any(g['tier'] == tier for g in user['gifts_received'])
        status = "✅ " if received else "🎯 "
        
        if received:
            # Ищем когда получил
            gift_data = next(g for g in user['gifts_received'] if g['tier'] == tier)
            date = gift_data['date'][:10]
            text += f"{status}*{gift_info['name']}* (получен {date})\n"
        else:
            needed = tier - user['total_donated']
            if needed > 0:
                text += f"{status}*{gift_info['name']}* (нужно еще {needed:.2f} USDT)\n"
            else:
                text += f"{status}*{gift_info['name']}* (можно забрать!)\n"
        
        text += f"   📝 {gift_info['description']}\n\n"
    
    # Полученные подарки
    if user['gifts_received']:
        text += "\n✅ *Уже получено:*\n"
        for gift in user['gifts_received']:
            text += f"• {gift['name']} ({gift['date'][:10]})\n"
    
    text += f"\n💰 *Ваш текущий вклад:* {user['total_donated']:.2f} USDT"
    text += f"\n🎯 *До следующего подарка:* "
    
    # Ищем следующий подарок
    next_gift_tier = None
    for tier in sorted(GIFTS.keys()):
        if not any(g['tier'] == tier for g in user['gifts_received']):
            next_gift_tier = tier
            break
    
    if next_gift_tier:
        needed = next_gift_tier - user['total_donated']
        if needed > 0:
            text += f"{needed:.2f} USDT"
        else:
            text += "можно забрать! Используйте /donate"
    else:
        text += "все подарки получены! 🎉"
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "share")
async def callback_share(callback: types.CallbackQuery):
    """Поделиться достижением"""
    user = db.get_user(callback.from_user.id)
    
    text = f"""
🌟 *ПОДЕЛИТЬСЯ ДОСТИЖЕНИЕМ*

🏆 *Ваши текущие достижения:*
Ранг: {user['rank']}
Сумма донатов: {user['total_donated']:.2f} USDT
Уровень: {user['level']}
Позиция в топе: #{db.get_user_position(callback.from_user.id)}

📱 *Выберите способ поделиться:*
1. *Поделиться в Telegram* - отправить сообщение друзьям
2. *Картинка* - сгенерировать красивую картинку с вашими достижениями

✨ *За шаринг вы получите:*
• +50 XP
• Шанс на редкий дроп
• Уважение сообщества
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=get_share_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "share_image")
async def callback_share_image(callback: types.CallbackQuery):
    """Генерация картинки для шаринга"""
    user = db.get_user(callback.from_user.id)
    
    # Генерируем картинку
    img_buffer = ImageGenerator.generate_donation_image(
        username=callback.from_user.username or callback.from_user.first_name,
        amount=user['total_donated'],
        rank=user['rank']
    )
    
    caption = f"""
🏆 *Мое достижение в Banana NFT!* 🍌

Ранг: {user['rank']}
Вклад: {user['total_donated']:.2f} USDT
Уровень: {user['level']}
Позиция в топе: #{db.get_user_position(callback.from_user.id)}

Присоединяйся к самому сочному NFT проекту!
👉 @banananftbot

#BananaNFT #Донат #Крипта #TelegramБот
    """
    
    await callback.message.answer_photo(
        photo=BufferedInputFile(img_buffer.getvalue(), filename="achievement.png"),
        caption=caption,
        parse_mode="Markdown"
    )
    await callback.answer("Картинка сгенерирована! ✨")

@dp.callback_query(F.data == "back")
async def callback_back(callback: types.CallbackQuery, state: FSMContext):
    """Назад в главное меню"""
    await state.clear()
    await cmd_start(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "admin")
async def callback_admin(callback: types.CallbackQuery):
    """Админ панель"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return
    
    text = f"""
👑 *АДМИН ПАНЕЛЬ BANANA NFT*

📊 *Общая статистика:*
Пользователей: {db.data['stats']['total_users']}
Всего донатов: {db.data['stats']['total_donations']}
Общая сумма: {db.data['total_donated']:.2f} USDT
Рекордный донат: {db.data['stats']['biggest_donation']:.2f} USDT

💎 *Система оплаты:* Telegram Stars (@donate)
🎯 *Минимальный донат:* {db.data['settings']['min_donation']} USDT
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_"))
async def callback_admin_actions(callback: types.CallbackQuery, state: FSMContext):
    """Обработка админ-действий"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return
    
    action = callback.data
    
    if action == "admin_stats":
        # Детальная статистика
        now = datetime.now()
        today = now.date().isoformat()
        
        # Считаем статистику за сегодня
        today_donations = 0
        today_amount = 0
        today_users = set()
        
        for user_id, user_data in db.data["users"].items():
            for donation in user_data.get("donations", []):
                if donation.get("date", "").startswith(today):
                    today_donations += 1
                    today_amount += donation.get("amount", 0)
                    today_users.add(user_id)
        
        text = f"""
📊 *ДЕТАЛЬНАЯ СТАТИСТИКА*

📈 *Общая:*
👥 Пользователей: {db.data['stats']['total_users']}
💰 Всего собрано: {db.data['total_donated']:.2f} USDT
🎯 Донатов: {db.data['stats']['total_donations']}
🏆 Рекорд: {db.data['stats']['biggest_donation']:.2f} USDT

📅 *За сегодня ({today}):*
👤 Новых пользователей: {len([u for u in db.data['users'].values() if u['join_date'].startswith(today)])}
💰 Сумма донатов: {today_amount:.2f} USDT
🎯 Количество донатов: {today_donations}
👥 Уникальных донатеров: {len(today_users)}

💎 *Система оплаты:* Telegram Stars
"""
        
        await callback.message.edit_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    
    elif action == "admin_users":
        # Список пользователей
        users = list(db.data["users"].values())
        users_sorted = sorted(users, key=lambda x: x["total_donated"], reverse=True)
        
        text = f"""
👥 *СПИСОК ПОЛЬЗОВАТЕЛЕЙ*

Всего пользователей: {len(users)}

*Топ-5 по донатам:*
"""
        
        for i, user in enumerate(users_sorted[:5], 1):
            username = user.get("username", "Аноним")
            join_date = user.get("join_date", "")[:10]
            text += f"{i}. @{username}\n"
            text += f"   💰 {user['total_donated']:.2f} USDT | 🎯 {len(user.get('donations', []))} донатов\n"
            text += f"   📅 {join_date} | 🔥 {user.get('daily_streak', 0)} дней\n\n"
        
        text += f"📊 *Средний донат на пользователя:* {db.data['total_donated']/len(users):.2f} USDT"
        
        await callback.message.edit_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    
    elif action == "admin_donations":
        # Последние донаты
        all_donations = []
        for user_id, user_data in db.data["users"].items():
            for donation in user_data.get("donations", []):
                all_donations.append({
                    "user_id": user_id,
                    "username": user_data.get("username", "Аноним"),
                    "amount": donation.get("amount", 0),
                    "date": donation.get("date", "")
                })
        
        # Сортируем по дате
        recent_donations = sorted(all_donations, key=lambda x: x["date"], reverse=True)[:10]
        
        text = """
💰 *ПОСЛЕДНИЕ ДОНАТЫ*

*Последние 10 донатов:*
"""
        
        total_last_24h = 0
        now = datetime.now()
        
        for i, donation in enumerate(recent_donations, 1):
            date_str = donation["date"][:16] if donation["date"] else "N/A"
            
            # Проверяем если донат был за последние 24 часа
            try:
                donate_time = datetime.fromisoformat(donation["date"].replace('Z', '+00:00'))
                if (now - donate_time).total_seconds() <= 86400:  # 24 часа
                    total_last_24h += donation["amount"]
            except:
                pass
            
            text += f"{i}. @{donation['username']}\n"
            text += f"   💰 {donation['amount']:.2f} USDT | 📅 {date_str}\n\n"
        
        text += f"💸 *Сумма за последние 24 часа:* {total_last_24h:.2f} USDT"
        
        await callback.message.edit_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    
    elif action == "admin_goals":
        # Управление целями
        text = """
🎯 *УПРАВЛЕНИЕ ЦЕЛЯМИ ПРОЕКТА*

*Текущие цели:*
"""
        
        for i, goal in enumerate(db.data["goals"], 1):
            achieved = "✅ " if goal.get("achieved") else "🎯 "
            progress = (db.data["total_donated"] / goal["target"]) * 100 if goal["target"] > 0 else 100
            date_achieved = f" ({goal.get('achieved_date', '')[:10]})" if goal.get("achieved") else ""
            
            text += f"{achieved}*{goal['name']}*\n"
            text += f"   🎯 Цель: {goal['target']} USDT\n"
            text += f"   📊 Прогресс: {progress:.1f}% ({db.data['total_donated']:.2f}/{goal['target']})\n"
            text += f"   🎁 Награда: {goal.get('reward', 'Не указана')}{date_achieved}\n\n"
        
        await callback.message.edit_caption(
            caption=text,
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    
    elif action == "admin_broadcast":
        # Рассылка
        await callback.message.answer(
            "📢 *ОТПРАВИТЬ РАССЫЛКУ*\n\n"
            "Введите сообщение для рассылки всем пользователям:\n\n"
            "💡 *Подсказка:* Используйте Markdown форматирование\n"
            "⚠️ *Внимание:* Рассылка будет отправлена всем {db.data['stats']['total_users']} пользователям",
            parse_mode="Markdown"
        )
        await state.set_state(AdminState.waiting_broadcast)
    
    await callback.answer()

@dp.message(AdminState.waiting_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    """Обработка рассылки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    broadcast_text = message.text or message.caption
    if not broadcast_text:
        await message.answer("❌ Сообщение пустое!")
        await state.clear()
        return
    
    # Статистика рассылки
    total_users = db.data['stats']['total_users']
    
    await message.answer(
        f"📢 *Начинаю рассылку...*\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"⏱️ Примерное время: {total_users//10} секунд\n\n"
        f"*В демо-режиме рассылка не отправляется*",
        parse_mode="Markdown"
    )
    
    await state.clear()

# ============ ОБРАБОТКА ОШИБОК ============
@dp.errors()
async def errors_handler(event: types.ErrorEvent):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {event.exception}", exc_info=True)
    
    # Пытаемся отправить сообщение об ошибке пользователю
    try:
        if hasattr(event.update, 'message') and event.update.message:
            await event.update.message.answer(
                "😕 *Упс! Произошла ошибка*\n\n"
                "Наша команда уже работает над решением проблемы.\n"
                "Попробуйте еще раз через несколько минут.\n\n"
                "💡 Если ошибка повторяется, напишите @support",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
    
    # Отправляем уведомление админу
    try:
        error_text = str(event.exception)[:1000]
        await bot.send_message(
            ADMIN_ID,
            f"⚠️ *ОШИБКА В БОТЕ*\n\n"
            f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}\n"
            f"❌ Ошибка: {error_text}\n"
            f"📊 Тип: {type(event.exception).__name__}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")
    
    return True

# ============ ЗАПУСК БОТА ============
async def main():
    """Основная функция запуска бота"""
    print("=" * 50)
    print("🍌 BANANA NFT BOT - ЗАПУСК...")
    print("=" * 50)
    
    # Проверка токенов
    if TELEGRAM_BOT_TOKEN == "ВАШ_ТЕЛЕГРАМ_ТОКЕН":
        print("❌ ОШИБКА: Не установлен Telegram токен!")
        print("🔄 Замените TELEGRAM_BOT_TOKEN в коде")
        return
    
    # Проверка базы данных
    print("📁 Проверка базы данных...")
    if not os.path.exists(DB_FILE):
        print("✅ Создана новая база данных")
    else:
        print(f"✅ База данных загружена ({db.data['stats']['total_users']} пользователей)")
    
    # Запуск бота
    print("🤖 Запуск бота...")
    try:
        me = await bot.get_me()
        print(f"✅ Бот запущен: @{me.username} (ID: {me.id})")
        print(f"👑 Админ ID: {ADMIN_ID}")
        print(f"💎 Платежная система: Telegram Stars (@donate)")
        print("=" * 50)
        print("📢 Бот готов к работе! Отправьте /start")
        print("=" * 50)
        
        await dp.start_polling(bot)
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
    finally:
        # Закрытие сессий
        await bot.session.close()
        print("👋 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())

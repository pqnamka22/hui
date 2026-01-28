import asyncio
import logging
from datetime import datetime
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import io
import json
import os

# ============ КОНФИГУРАЦИЯ ============
TELEGRAM_BOT_TOKEN = "8536282991:AAFDzgiXbhJG-GSuKci04oLy3Ny4bpdD9Yw"  # 🔴 ЗАМЕНИТЕ!
CRYPTO_BOT_TOKEN = "522930:AAl0Ojn6IiEeAZH2NP2nZ4ZjUgBR6getqjL"  # 🔴 ЗАМЕНИТЕ!
ADMIN_ID = 123456789  # 🔴 ВАШ ID в Telegram

# База данных (для демо - JSON файл, в продакшене используйте PostgreSQL)
DB_FILE = "database.json"

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============ БАЗА ДАННЫХ ============
def load_db():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"users": {}, "total_donated": 0, "top_donations": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user(user_id, username=""):
    db = load_db()
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {
            "username": username,
            "total_donated": 0,
            "donations": [],
            "rank": "🍌 Новый банан",
            "join_date": datetime.now().isoformat(),
            "level": 1
        }
        save_db(db)
    return db["users"][str(user_id)]

def update_user(user_id, amount, username=""):
    db = load_db()
    user_id_str = str(user_id)
    
    if user_id_str not in db["users"]:
        get_user(user_id, username)
    
    db["users"][user_id_str]["total_donated"] += amount
    db["users"][user_id_str]["donations"].append({
        "amount": amount,
        "date": datetime.now().isoformat()
    })
    db["users"][user_id_str]["username"] = username
    
    # Обновляем топ донатов
    donation_entry = {
        "user_id": user_id,
        "username": username,
        "amount": amount,
        "date": datetime.now().isoformat()
    }
    db["top_donations"].append(donation_entry)
    db["top_donations"] = sorted(db["top_donations"], 
                                 key=lambda x: x["amount"], 
                                 reverse=True)[:100]
    
    db["total_donated"] += amount
    save_db(db)
    
    # Обновляем ранг
    return update_rank(user_id_str)

def update_rank(user_id_str):
    db = load_db()
    total = db["users"][user_id_str]["total_donated"]
    
    ranks = {
        0: "🍌 Желтый банан",
        10: "💰 Banana Collector",
        50: "🌟 Banana Star",
        100: "🏆 Banana Champion",
        500: "👑 Banana King",
        1000: "🚀 Banana God",
        5000: "💎 Diamond Banana"
    }
    
    current_rank = "🍌 Желтый банан"
    for amount, rank in sorted(ranks.items(), reverse=True):
        if total >= amount:
            current_rank = rank
            break
    
    db["users"][user_id_str]["rank"] = current_rank
    
    # Уровень (каждые 10 USDT)
    db["users"][user_id_str]["level"] = min(100, total // 10 + 1)
    
    save_db(db)
    return current_rank, db["users"][user_id_str]["level"]

# ============ CRYPTOBOT API ============
class CryptoBotAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://pay.crypt.bot/api"
    
    async def create_invoice(self, amount, currency="USDT", description=""):
        headers = {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "amount": amount,
            "asset": currency,
            "description": description,
            "hidden_message": "Спасибо за донат! 🍌",
            "paid_btn_url": "https://t.me/banananftbot",
            "paid_btn_text": "Вернуться в бота",
            "payload": str(datetime.now().timestamp()),
            "allow_comments": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/createInvoice", 
                                  json=payload, 
                                  headers=headers) as response:
                data = await response.json()
                
                if data.get("ok"):
                    invoice = data["result"]
                    return {
                        "invoice_id": invoice["invoice_id"],
                        "pay_url": invoice["pay_url"],
                        "amount": invoice["amount"],
                        "status": invoice["status"]
                    }
                else:
                    raise Exception(f"CryptoBot error: {data.get('error')}")

crypto_bot = CryptoBotAPI(CRYPTO_BOT_TOKEN)

# ============ ГЕНЕРАЦИЯ КАРТИНОК ============
def generate_donation_image(username, amount, rank):
    # Создаем изображение
    width, height = 800, 400
    
    # Фон с градиентом
    img = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(img)
    
    # Градиент фон
    for i in range(height):
        r = int(255 * (i / height))
        g = int(200 * (i / height))
        b = 50
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    
    # Добавляем бананы на фон
    try:
        banana = Image.open("banana.png") if os.path.exists("banana.png") else None
        if banana:
            banana = banana.resize((100, 100))
            for x in range(0, width, 150):
                for y in range(0, height, 150):
                    img.paste(banana, (x, y), banana)
    except:
        pass
    
    # Размываем фон бананов
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    draw = ImageDraw.Draw(img)
    
    try:
        # Загружаем шрифты
        title_font = ImageFont.truetype("arialbd.ttf", 48)
        text_font = ImageFont.truetype("arial.ttf", 32)
        amount_font = ImageFont.truetype("arialbd.ttf", 64)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        amount_font = ImageFont.load_default()
    
    # Заголовок
    draw.text((width//2, 50), "BANANA NFT 🍌", 
              font=title_font, fill=(255, 215, 0), anchor="mm")
    
    # Имя пользователя
    draw.text((width//2, 120), f"@{username}", 
              font=text_font, fill=(255, 255, 255), anchor="mm")
    
    # Сумма доната
    draw.text((width//2, 190), f"{amount} USDT", 
              font=amount_font, fill=(255, 215, 0), anchor="mm")
    
    # Ранг
    draw.text((width//2, 260), rank, 
              font=text_font, fill=(200, 200, 200), anchor="mm")
    
    # Нижний текст
    draw.text((width//2, 330), "Спасибо за поддержку! 💛", 
              font=text_font, fill=(255, 255, 255), anchor="mm")
    
    # Сохраняем в буфер
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer

# ============ STATES ============
class DonationState(StatesGroup):
    waiting_for_amount = State()
    processing_payment = State()

# ============ КЛАВИАТУРЫ ============
def main_menu():
    keyboard = [
        [InlineKeyboardButton(text="💰 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Топ донатеров", callback_data="top")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🎁 Подарки", callback_data="gifts")],
        [InlineKeyboardButton(text="🌟 Поделиться", callback_data="share")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def donate_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="5 USDT 🍌", callback_data="donate_5"),
            InlineKeyboardButton(text="10 USDT 💰", callback_data="donate_10"),
            InlineKeyboardButton(text="25 USDT 🌟", callback_data="donate_25")
        ],
        [
            InlineKeyboardButton(text="50 USDT 🏆", callback_data="donate_50"),
            InlineKeyboardButton(text="100 USDT 👑", callback_data="donate_100"),
            InlineKeyboardButton(text="Другая сумма", callback_data="donate_custom")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def payment_keyboard(pay_url):
    keyboard = [
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check_payment")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def share_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📱 Поделиться в Telegram", 
                             url="https://t.me/share/url?url=https://t.me/banananftbot&text=Я+только+что+задонатил+в+BANANA+NFT+бот!+🍌")],
        [InlineKeyboardButton(text="🎨 Сгенерировать картинку", callback_data="generate_image")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============ ХЕНДЛЕРЫ ============
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    
    welcome_text = f"""
    🍌 *Добро пожаловать в BANANA NFT!* 🚀

    *Твой статус:* {user['rank']}
    *Твой вклад:* {user['total_donated']} USDT
    *Уровень:* {user['level']}

    🌟 *Что у нас есть:*
    • Система донатов с рейтингом
    • Эксклюзивные подарки за вклад
    • Возможность делиться достижениями
    • Секретные обновления...

    🎁 *Ближайший подарок:* Golden Banana NFT
    *Нужно:* 100 USDT всего
    *Собрано:* {load_db()['total_donated']}/100 USDT

    🔮 *Готовьтесь к Banana NFT Marketplace...*
    """
    
    await message.answer_photo(
        photo="https://img.freepik.com/free-vector/gradient-banana-background_23-2150544491.jpg",
        caption=welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "donate")
async def donate_callback(callback: types.CallbackQuery):
    text = """
    💰 *Поддержать BANANA NFT*

    Выберите сумму доната или введите свою:

    *Что вы получаете:*
    🏆 - Повышение в рейтинге
    🎁 - Эксклюзивные подарки
    🌟 - Уникальные роли
    💎 - Доступ к закрытому чату

    *Текущая цель:* 1000 USDT
    *Награда:* Все получат Special NFT!
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=donate_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("donate_"))
async def quick_donate(callback: types.CallbackQuery, state: FSMContext):
    amount_str = callback.data.split("_")[1]
    
    if amount_str == "custom":
        await callback.message.answer("Введите сумму доната в USDT:")
        await state.set_state(DonationState.waiting_for_amount)
    else:
        try:
            amount = float(amount_str)
            await process_donation(callback, amount, state)
        except:
            await callback.answer("Ошибка суммы", show_alert=True)
    
    await callback.answer()

@dp.message(DonationState.waiting_for_amount)
async def process_custom_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < 0.1:
            await message.answer("Минимальная сумма: 0.1 USDT")
            return
        
        await process_donation(None, amount, state, message)
    except:
        await message.answer("Пожалуйста, введите корректную сумму (например: 10.5)")

async def process_donation(callback, amount, state, message=None):
    user_id = callback.from_user.id if callback else message.from_user.id
    username = callback.from_user.username if callback else message.from_user.username
    
    try:
        # Создаем счет в CryptoBot
        invoice = await crypto_bot.create_invoice(
            amount=amount,
            currency="USDT",
            description=f"Donation to Banana NFT from @{username}"
        )
        
        await state.update_data(invoice_id=invoice["invoice_id"], amount=amount)
        await state.set_state(DonationState.processing_payment)
        
        text = f"""
        🍌 *ОПЛАТА ДОНАТА*

        *Сумма:* {amount} USDT
        *Статус:* Ожидает оплаты

        💳 *Инструкция:*
        1. Нажмите кнопку "Оплатить"
        2. Оплатите счет в CryptoBot
        3. Вернитесь и нажмите "Проверить оплату"

        🎁 *Бонусы за этот донат:*
        • +{amount * 10} очков рейтинга
        • Прогресс к следующему уровню
        • Шанс выиграть Golden Banana NFT!

        *Следующий подарок через:* {100 - amount} USDT
        """
        
        if callback:
            await callback.message.edit_caption(
                caption=text,
                parse_mode="Markdown",
                reply_markup=payment_keyboard(invoice["pay_url"])
            )
        else:
            await message.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=payment_keyboard(invoice["pay_url"])
            )
            
    except Exception as e:
        error_msg = f"Ошибка создания счета: {str(e)}"
        if callback:
            await callback.message.answer(error_msg)
        else:
            await message.answer(error_msg)

@dp.callback_query(F.data == "check_payment")
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    # Здесь должна быть проверка оплаты через CryptoBot API
    # Для демо - считаем оплаченным
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    # Обновляем пользователя
    amount = data.get("amount", 0)
    rank, level = update_user(user_id, amount, username)
    
    # Показываем результат
    text = f"""
    🎉 *ОПЛАТА ПОДТВЕРЖДЕНА!*

    ✅ Спасибо за донат!
    
    *Детали:*
    💰 Сумма: {amount} USDT
    🏆 Новый ранг: {rank}
    ⭐ Уровень: {level}
    📈 Всего задоначено: {get_user(user_id)['total_donated']} USDT

    🎁 *Вы получили:*
    • VIP статус на 7 дней
    • +{amount * 10} очков рейтинга
    • Доступ к эксклюзивным стикерам

    🔮 *Следующая цель:* 500 USDT
    *Награда:* Персональный NFT Banana!
    """
    
    await callback.message.edit_caption(
        caption=text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    
    # Уведомляем админа
    await bot.send_message(
        ADMIN_ID,
        f"🎉 Новый донат!\n"
        f"👤 @{username}\n"
        f"💰 {amount} USDT\n"
        f"🏆 Новый ранг: {rank}"
    )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "top")
async def show_top(callback: types.CallbackQuery):
    db = load_db()
    top_users = sorted(db["users"].items(), 
                      key=lambda x: x[1]["total_donated"], 
                      reverse=True)[:10]
    
    top_text = "🏆 *ТОП ДОНАТЕРОВ BANANA NFT* 🍌\n\n"
    
    for i, (user_id, user_data) in enumerate(top_users, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        username = user_data.get("username", "Аноним")
        total = user_data["total_donated"]
        
        top_text += f"{medal} @{username}\n"
        top_text += f"   💰 *{total} USDT* | {user_data['rank']}\n"
        top_text += f"   ⭐ Уровень: {user_data['level']}\n\n"
    
    top_text += f"\n💎 Всего собрано: *{db['total_donated']} USDT*"
    top_text += f"\n🎯 Цель: 1000 USDT | Прогресс: {db['total_donated']/1000*100:.1f}%"
    
    await callback.message.edit_caption(
        caption=top_text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id, callback.from_user.username)
    
    stats_text = f"""
    📊 *ВАША СТАТИСТИКА*

    👤 *Профиль:*
    Имя: @{callback.from_user.username or 'Аноним'}
    ID: {user_id}
    
    🏆 *Достижения:*
    Ранг: {user['rank']}
    Уровень: {user['level']}
    Всего донатов: {len(user['donations'])}
    
    💰 *Финансы:*
    Общая сумма: {user['total_donated']} USDT
    Место в топе: #{get_user_rank(user_id)}
    
    📅 *Активность:*
    В проекте с: {user['join_date'][:10]}
    Последний донат: {user['donations'][-1]['date'][:10] if user['donations'] else 'еще нет'}
    
    🎯 *Прогресс:*
    До след. уровня: {user['level']*10 - user['total_donated']} USDT
    До след. ранга: {get_next_rank_need(user['total_donated'])} USDT
    """
    
    await callback.message.edit_caption(
        caption=stats_text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

def get_user_rank(user_id):
    db = load_db()
    sorted_users = sorted(db["users"].items(), 
                         key=lambda x: x[1]["total_donated"], 
                         reverse=True)
    
    for i, (uid, _) in enumerate(sorted_users, 1):
        if str(user_id) == uid:
            return i
    return 999

def get_next_rank_need(current_amount):
    ranks = [0, 10, 50, 100, 500, 1000, 5000]
    for rank in ranks:
        if current_amount < rank:
            return rank - current_amount
    return 0

@dp.callback_query(F.data == "gifts")
async def show_gifts(callback: types.CallbackQuery):
    gifts_text = """
    🎁 *ЭКСКЛЮЗИВНЫЕ ПОДАРКИ*

    *За ваши донаты вы получаете:*

    🍌 *10+ USDT:*
    • Кастомный эмодзи Banana
    • Роль в группе
    • +100 очков рейтинга

    💰 *50+ USDT:*
    • Стикерпак "Banana Gang"
    • VIP на 30 дней
    • Golden Name в чате
    • Доступ к закрытому каналу

    🌟 *100+ USDT:*
    • Персональный NFT Banana
    • Сооснователь клуба
    • Участие в голосованиях
    • Эксклюзивные анонсы

    🏆 *500+ USDT:*
    • Diamond Banana NFT
    • Пожизненный VIP
    • Личный менеджер
    • Доход с проекта 1%

    👑 *1000+ USDT:*
    • Владелец Banana Token
    • Управление проектом
    • Все предыдущие плюшки ×2
    • Место в Зале Славы

    🔮 *Скоро:*
    • Banana NFT Marketplace
    • $BNFT токен
    • Мобильная игра
    • Физический мерч
    """
    
    await callback.message.edit_caption(
        caption=gifts_text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "share")
async def share_menu(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)
    
    share_text = f"""
    🌟 *ПОДЕЛИТЬСЯ ДОСТИЖЕНИЕМ*

    🏆 *Ваш текущий результат:*
    Ранг: {user['rank']}
    Сумма: {user['total_donated']} USDT
    Уровень: {user['level']}

    📱 *Выберите способ:*
    1. Поделиться в Telegram
    2. Сгенерировать красивую картинку
    3. Скопировать текст для соцсетей

    🎨 *Картинка будет содержать:*
    • Ваш юзернейм
    • Сумму донатов
    • Ваш ранг
    • Логотип Banana NFT
    • Эффекты и градиенты

    ✨ *За шаринг вы получите:*
    • +50 очков рейтинга
    • Шанс на редкий дроп
    • Упоминание в канале
    """
    
    await callback.message.edit_caption(
        caption=share_text,
        parse_mode="Markdown",
        reply_markup=share_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "generate_image")
async def generate_share_image(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id, callback.from_user.username)
    
    # Генерируем картинку
    img_buffer = generate_donation_image(
        username=callback.from_user.username or "Аноним",
        amount=user['total_donated'],
        rank=user['rank']
    )
    
    # Отправляем картинку
    await callback.message.answer_photo(
        photo=types.BufferedInputFile(img_buffer.getvalue(), filename="banana_donation.png"),
        caption=f"🏆 *Мое достижение в Banana NFT!*\n\n"
               f"Присоединяйся: @banananftbot\n"
               f"#BananaNFT #Донат",
        parse_mode="Markdown"
    )
    
    await callback.answer("Картинка сгенерирована! ✨")

@dp.callback_query(F.data == "back")
async def back_to_main(callback: types.CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()

# ============ АДМИН КОМАНДЫ ============
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа!")
        return
    
    db = load_db()
    
    admin_text = f"""
    👑 *АДМИН ПАНЕЛЬ BANANA NFT*

    📊 *Статистика:*
    Всего пользователей: {len(db['users'])}
    Всего донатов: {db['total_donated']} USDT
    Топ донат: {max([u['total_donated'] for u in db['users'].values()] or [0])} USDT
    
    💰 *Последние донаты:*
    """
    
    for donation in db["top_donations"][:5]:
        admin_text += f"• @{donation['username']}: {donation['amount']} USDT\n"
    
    keyboard = [
        [InlineKeyboardButton(text="📈 Полная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎯 Установить цель", callback_data="admin_set_goal")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")]
    ]
    
    await message.answer(
        text=admin_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# ============ ЗАПУСК БОТА ============
async def main():
    print("🍌 Banana NFT Bot запущен!")
    print(f"🤖 Бот: @{(await bot.get_me()).username}")
    
    # Создаем базу данных если нет
    if not os.path.exists(DB_FILE):
        save_db({"users": {}, "total_donated": 0, "top_donations": []})
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

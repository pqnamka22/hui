import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart

API_TOKEN = "8536282991:AAFDzgiXbhJG-GSuKci04oLy3Ny4bpdD9Yw"

logging.basicConfig(level=logging.INFO)

bot = Bot(API_TOKEN)
dp = Dispatcher()

# ======================
# IN-MEMORY STORAGE
# ======================
users_spent = {}   # user_id -> stars spent
awaiting_custom = set()  # user_ids waiting custom amount


# ======================
# UI
# ======================
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 10", callback_data="pay_10"),
            InlineKeyboardButton(text="⭐ 50", callback_data="pay_50"),
            InlineKeyboardButton(text="⭐ 100", callback_data="pay_100"),
        ],
        [
            InlineKeyboardButton(text="🔥 500", callback_data="pay_500"),
            InlineKeyboardButton(text="💎 1000", callback_data="pay_1000"),
        ],
        [
            InlineKeyboardButton(text="✍️ Своя сумма", callback_data="custom"),
        ],
        [
            InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rating"),
        ]
    ])


# ======================
# HELPERS
# ======================
def add_spent(user_id: int, amount: int):
    users_spent[user_id] = users_spent.get(user_id, 0) + amount


def get_place(user_id: int):
    sorted_users = sorted(users_spent.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, _) in enumerate(sorted_users, start=1):
        if uid == user_id:
            return i
    return None


# ======================
# HANDLERS
# ======================
@dp.message(CommandStart())
async def start(msg: Message):
    await msg.answer(
        "🍌 *BANANA · BE RICH*\n\n"
        "Тут не покупают NFT.\n"
        "Тут *сжигают деньги*, чтобы все знали, кто жирнее.\n\n"
        "👇 Выбирай сумму:",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("pay_"))
async def pay(call: CallbackQuery):
    amount = int(call.data.split("_")[1])
    uid = call.from_user.id

    add_spent(uid, amount)
    place = get_place(uid)

    await call.message.answer(
        f"🔥 Ты сжёг *{amount} ⭐*\n"
        f"💰 Всего: *{users_spent[uid]} ⭐*\n"
        f"🏆 Место в топе: *#{place}*",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )
    await call.answer()


@dp.callback_query(F.data == "custom")
async def custom(call: CallbackQuery):
    awaiting_custom.add(call.from_user.id)
    await call.message.answer(
        "✍️ Введи сумму звезд (число):"
    )
    await call.answer()


@dp.message(F.text.regexp(r"^\d+$"))
async def custom_amount(msg: Message):
    uid = msg.from_user.id
    if uid not in awaiting_custom:
        return

    amount = int(msg.text)
    awaiting_custom.remove(uid)

    if amount <= 0 or amount > 1_000_000:
        await msg.answer("❌ Сумма неадекватна.")
        return

    add_spent(uid, amount)
    place = get_place(uid)

    await msg.answer(
        f"🔥 КРАСИВО.\n"
        f"Ты въебал *{amount} ⭐*\n\n"
        f"💰 Всего: *{users_spent[uid]} ⭐*\n"
        f"🏆 Ты теперь *#{place}*",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )


@dp.callback_query(F.data == "rating")
async def rating(call: CallbackQuery):
    if not users_spent:
        await call.message.answer("Пока никто не сжёг ни копейки.")
        await call.answer()
        return

    top = sorted(users_spent.items(), key=lambda x: x[1], reverse=True)[:10]

    text = "🏆 *ТОП ЖИРНЫХ*\n\n"
    for i, (uid, total) in enumerate(top, start=1):
        text += f"{i}. {uid} — *{total} ⭐*\n"

    await call.message.answer(text, parse_mode="Markdown", reply_markup=main_kb())
    await call.answer()


# ======================
# RUN
# ======================
async def main():
    await dp.start_polling(bot)


if name == "__main__":
    asyncio.run(main())

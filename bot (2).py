import asyncio
import logging
import uuid
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8536282991:AAFDzgiXbhJG-GSuKci04oLy3Ny4bpdD9Yw"
CRYPTOBOT_TOKEN = "522930:AAl0Ojn6IiEeAZH2NP2nZ4ZjUgBR6getqjL"

CRYPTOBOT_API = "https://pay.crypt.bot/api"

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ======================
# STORAGE (IN-MEMORY)
# ======================
users_spent = {}           # user_id -> total USDT
pending_invoices = {}     # invoice_id -> user_id


# ======================
# UI
# ======================
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 5 USDT", callback_data="pay_5"),
            InlineKeyboardButton(text="💸 10 USDT", callback_data="pay_10"),
        ],
        [
            InlineKeyboardButton(text="🔥 25 USDT", callback_data="pay_25"),
            InlineKeyboardButton(text="💎 50 USDT", callback_data="pay_50"),
        ],
        [
            InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rating"),
        ]
    ])


# ======================
# CRYPTOBOT API
# ======================
async def create_invoice(amount: float, user_id: int):
    invoice_id = str(uuid.uuid4())

    payload = {
        "asset": "USDT",
        "amount": amount,
        "description": "BANANA · BE RICH",
        "hidden_message": "Ты реально это сделал.",
        "payload": invoice_id,
        "allow_comments": False,
        "expires_in": 3600
    }

    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CRYPTOBOT_API}/createInvoice",
            json=payload,
            headers=headers
        ) as resp:
            data = await resp.json()

    if not data.get("ok"):
        raise Exception(data)

    pending_invoices[invoice_id] = user_id
    return data["result"]["pay_url"]


async def check_invoice(invoice_id: str):
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CRYPTOBOT_API}/getInvoices",
            params={"asset": "USDT", "invoice_ids": invoice_id},
            headers=headers
        ) as resp:
            data = await resp.json()

    if not data.get("ok"):
        return False

    items = data["result"]["items"]
    if not items:
        return False

    return items[0]["status"] == "paid", float(items[0]["amount"])


# ======================
# HELPERS
# ======================
def add_spent(uid: int, amount: float):
    users_spent[uid] = users_spent.get(uid, 0) + amount


def get_place(uid: int):
    sorted_users = sorted(users_spent.items(), key=lambda x: x[1], reverse=True)
    for i, (u, _) in enumerate(sorted_users, 1):
        if u == uid:
            return i
    return None


# ======================
# HANDLERS
# ======================
@dp.message(CommandStart())
async def start(msg: Message):
    await msg.answer(
        "🍌 *BANANA · BE RICH*\n\n"
        "Здесь не инвестируют.\n"
        "Здесь *сжигают USDT*, чтобы все видели.\n\n"
        "👇 Выбирай сумму:",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("pay_"))
async def pay(call: CallbackQuery):
    amount = float(call.data.split("_")[1])
    uid = call.from_user.id

    url = await create_invoice(amount, uid)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Оплатить", url=url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{url.split('=')[-1]}")]
    ])

    await call.message.answer(
        f"💸 *{amount} USDT*\n\n"
        "Нажми «Оплатить», потом «Проверить оплату».",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await call.answer()


@dp.callback_query(F.data.startswith("check_"))
async def check(call: CallbackQuery):
    invoice_id = call.data.replace("check_", "")

    if invoice_id not in pending_invoices:
        await call.answer("Инвойс не найден", show_alert=True)
        return

    paid, amount = await check_invoice(invoice_id)
    if not paid:
        await call.answer("❌ Пока не оплачено")
        return

    uid = pending_invoices.pop(invoice_id)
    add_spent(uid, amount)
    place = get_place(uid)

    await call.message.answer(
        f"🔥 *ОПЛАЧЕНО*\n\n"
        f"Ты сжёг *{amount} USDT*\n"
        f"💰 Всего: *{users_spent[uid]} USDT*\n"
        f"🏆 Место: *#{place}*",
        parse_mode="Markdown",
        reply_markup=main_kb()
    )
    await call.answer("✅ Успешно")


@dp.callback_query(F.data == "rating")
async def rating(call: CallbackQuery):
    if not users_spent:
        await call.message.answer("Пока никто не сжёг USDT.")
        await call.answer()
        return

    top = sorted(users_spent.items(), key=lambda x: x[1], reverse=True)[:10]

    text = "🏆 *ТОП КИТОВ*\n\n"
    for i, (uid, total) in enumerate(top, 1):
        text += f"{i}. {uid} — *{total} USDT*\n"

    await call.message.answer(text, parse_mode="Markdown", reply_markup=main_kb())
    await call.answer()


# ======================
# RUN
# ======================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

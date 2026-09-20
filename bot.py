import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import os
from dotenv import load_dotenv

from database import init_db, get_or_create_user, get_user, admin_give_stars, ban_user, get_stats

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")  # Замени на свой URL (ngrok и т.д.)
ADMIN_ID = 7569976612

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except:
            pass
    
    await get_or_create_user(user.id, user.username, user.first_name, referrer_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 Играть",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )],
        [InlineKeyboardButton(text="⭐ Баланс", callback_data="balance"),
         InlineKeyboardButton(text="🏆 Лидеры", callback_data="leaders")],
        [InlineKeyboardButton(text="📋 Помощь", callback_data="help")]
    ])
    
    await message.answer(
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"Это <b>GiftChase Virtual</b> — виртуальный азартный бот на звёздах ⭐\n\n"
        f"Все игры полностью виртуальные. Реальных денег нет.\n\n"
        f"Нажми кнопку ниже, чтобы открыть игру:",
        reply_markup=kb
    )

@dp.callback_query(F.data == "balance")
async def cb_balance(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала /start", show_alert=True)
        return
    await callback.message.answer(
        f"💰 Твой баланс: <b>{user['balance']}</b> ⭐\n"
        f"Всего выиграно: {user['total_won']} ⭐\n"
        f"Игр сыграно: {user['games_played']}"
    )
    await callback.answer()

@dp.callback_query(F.data == "leaders")
async def cb_leaders(callback: types.CallbackQuery):
    from database import get_leaderboard
    leaders = await get_leaderboard(10)
    text = "🏆 <b>Топ игроков</b>\n\n"
    for i, u in enumerate(leaders, 1):
        name = u.get("first_name") or u.get("username") or str(u["user_id"])
        text += f"{i}. {name} — <b>{u['balance']}</b> ⭐\n"
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "help")
async def cb_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "📖 <b>Как играть</b>\n\n"
        "• <b>Ракета</b> — ставь звёзды и забирай на нужном множителе\n"
        "• <b>Мины</b> — открывай клетки, избегай мин\n"
        "• <b>Слоты</b> — крути барабаны\n"
        "• <b>PVP</b> — сражайся с другими игроками\n"
        "• <b>Апгрейд</b> — улучшай виртуальные подарки\n\n"
        "Всё виртуально. Удачи! 🍀"
    )
    await callback.answer()

# Admin commands
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = await get_stats()
    await message.answer(
        f"🛠 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"⭐ Всего звёзд в системе: {stats['total_balance']}\n"
        f"🎮 Игр сыграно: {stats['total_games']}\n"
        f"💰 Всего выиграно: {stats['total_won']}\n\n"
        f"Команды:\n"
        f"/give USER_ID AMOUNT — выдать звёзды\n"
        f"/ban USER_ID — забанить\n"
        f"/unban USER_ID — разбанить"
    )

@dp.message(Command("give"))
async def cmd_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        amount = int(parts[2])
        ok = await admin_give_stars(uid, amount)
        if ok:
            await message.answer(f"✅ Выдано {amount} ⭐ пользователю {uid}")
        else:
            await message.answer("❌ Ошибка")
    except:
        await message.answer("Использование: /give USER_ID AMOUNT")

@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(message.text.split()[1])
        await ban_user(uid, True)
        await message.answer(f"🚫 Пользователь {uid} забанен")
    except:
        await message.answer("Использование: /ban USER_ID")

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(message.text.split()[1])
        await ban_user(uid, False)
        await message.answer(f"✅ Пользователь {uid} разбанен")
    except:
        await message.answer("Использование: /unban USER_ID")

async def main():
    await init_db()
    logger.info("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

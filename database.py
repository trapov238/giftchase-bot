import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

DB_PATH = "giftchase.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance INTEGER DEFAULT 1000,
                total_won INTEGER DEFAULT 0,
                total_lost INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                referrer_id INTEGER,
                created_at TEXT,
                last_active TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                gift_name TEXT,
                gift_emoji TEXT,
                value INTEGER,
                rarity TEXT DEFAULT 'common',
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                bet INTEGER,
                result TEXT,
                multiplier REAL,
                profit INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pvp_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                bet_amount INTEGER,
                status TEXT DEFAULT 'waiting',
                player2_id INTEGER,
                winner_id INTEGER,
                created_at TEXT
            )
        """)
        await db.commit()

async def get_or_create_user(user_id: int, username: str = None, first_name: str = None, referrer_id: int = None) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if user:
            await db.execute(
                "UPDATE users SET last_active = ?, username = COALESCE(?, username), first_name = COALESCE(?, first_name) WHERE user_id = ?",
                (datetime.now().isoformat(), username, first_name, user_id)
            )
            await db.commit()
            return dict(user)
        
        # New user
        is_admin = 1 if user_id == 7569976612 else 0
        await db.execute(
            """INSERT INTO users (user_id, username, first_name, balance, is_admin, referrer_id, created_at, last_active)
               VALUES (?, ?, ?, 1000, ?, ?, ?, ?)""",
            (user_id, username, first_name, is_admin, referrer_id, datetime.now().isoformat(), datetime.now().isoformat())
        )
        await db.commit()
        
        # Referral bonus
        if referrer_id:
            await db.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (referrer_id,))
            await db.commit()
        
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        return dict(user)

async def get_user(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        return dict(user) if user else None

async def update_balance(user_id: int, amount: int, is_win: bool = False) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance, is_banned FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row or row[1]:
            return False
        new_balance = row[0] + amount
        if new_balance < 0:
            return False
        
        if is_win and amount > 0:
            await db.execute(
                "UPDATE users SET balance = ?, total_won = total_won + ?, games_played = games_played + 1 WHERE user_id = ?",
                (new_balance, amount, user_id)
            )
        elif amount < 0:
            await db.execute(
                "UPDATE users SET balance = ?, total_lost = total_lost + ?, games_played = games_played + 1 WHERE user_id = ?",
                (new_balance, abs(amount), user_id)
            )
        else:
            await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        await db.commit()
        return True

async def add_history(user_id: int, game_type: str, bet: int, result: str, multiplier: float = 1.0, profit: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO history (user_id, game_type, bet, result, multiplier, profit, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, game_type, bet, result, multiplier, profit, datetime.now().isoformat())
        )
        await db.commit()

async def get_leaderboard(limit: int = 20) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT user_id, username, first_name, balance, total_won, games_played 
               FROM users WHERE is_banned = 0 
               ORDER BY balance DESC LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_user_gifts(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM gifts WHERE user_id = ? ORDER BY value DESC", (user_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def add_gift(user_id: int, gift_name: str, gift_emoji: str, value: int, rarity: str = "common"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO gifts (user_id, gift_name, gift_emoji, value, rarity, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, gift_name, gift_emoji, value, rarity, datetime.now().isoformat())
        )
        await db.commit()

async def ban_user(user_id: int, ban: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if ban else 0, user_id))
        await db.commit()

async def admin_give_stars(user_id: int, amount: int) -> bool:
    return await update_balance(user_id, amount)

async def get_stats() -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT SUM(balance) FROM users")
        total_balance = (await cursor.fetchone())[0] or 0
        cursor = await db.execute("SELECT COUNT(*) FROM history")
        total_games = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT SUM(total_won) FROM users")
        total_won = (await cursor.fetchone())[0] or 0
        return {
            "total_users": total_users,
            "total_balance": total_balance,
            "total_games": total_games,
            "total_won": total_won
        }

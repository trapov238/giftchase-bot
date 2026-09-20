from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os

from database import (
    init_db, get_or_create_user, get_user, update_balance, add_history,
    get_leaderboard, get_user_gifts, add_gift, ban_user, admin_give_stars, get_stats
)
from games.rocket import play_rocket, generate_crash_point
from games.mines import play_mines
from games.slots import play_slots
from games.upgrade import play_upgrade
from games.pvp import create_room, join_room, get_waiting_rooms

app = FastAPI(title="GiftChase Virtual")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ADMIN_ID = 7569976612

class BetRequest(BaseModel):
    user_id: int
    amount: int
    extra: Optional[dict] = None

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/user/{user_id}")
async def api_get_user(user_id: int, username: str = None, first_name: str = None):
    user = await get_or_create_user(user_id, username, first_name)
    if user.get("is_banned"):
        raise HTTPException(403, "Вы заблокированы")
    gifts = await get_user_gifts(user_id)
    return {"user": user, "gifts": gifts}

@app.get("/api/leaderboard")
async def api_leaderboard():
    return await get_leaderboard(50)

@app.post("/api/rocket")
async def api_rocket(data: BetRequest):
    user = await get_user(data.user_id)
    if not user or user["is_banned"]:
        raise HTTPException(403, "Доступ запрещён")
    if data.amount < 1 or data.amount > user["balance"]:
        raise HTTPException(400, "Недостаточно звёзд")
    
    cashout = data.extra.get("cashout") if data.extra else None
    
    if cashout:
        # Actual play
        result = play_rocket(data.amount, float(cashout))
        if not result.get("success"):
            raise HTTPException(400, result.get("error", "Ошибка"))
        
        if result["win"]:
            await update_balance(data.user_id, result["profit"], is_win=True)
            await add_history(data.user_id, "rocket", data.amount, "win", result["cashout"], result["profit"])
        else:
            await update_balance(data.user_id, -data.amount)
            await add_history(data.user_id, "rocket", data.amount, "lose", result["crash"], -data.amount)
        
        return result
    else:
        # Just get next crash for animation (demo mode)
        crash = generate_crash_point()
        return {"crash": crash}

@app.post("/api/mines")
async def api_mines(data: BetRequest):
    user = await get_user(data.user_id)
    if not user or user["is_banned"]:
        raise HTTPException(403, "Доступ запрещён")
    if data.amount < 1 or data.amount > user["balance"]:
        raise HTTPException(400, "Недостаточно звёзд")
    
    mines_count = data.extra.get("mines", 3) if data.extra else 3
    revealed = data.extra.get("revealed", []) if data.extra else []
    cashout = data.extra.get("cashout", False) if data.extra else False
    
    result = play_mines(data.amount, mines_count, revealed, cashout)
    
    if result.get("win") is True:
        await update_balance(data.user_id, result["profit"], is_win=True)
        await add_history(data.user_id, "mines", data.amount, "win", result["multiplier"], result["profit"])
    elif result.get("win") is False:
        await update_balance(data.user_id, -data.amount)
        await add_history(data.user_id, "mines", data.amount, "lose", 0, -data.amount)
    
    return result

@app.post("/api/slots")
async def api_slots(data: BetRequest):
    user = await get_user(data.user_id)
    if not user or user["is_banned"]:
        raise HTTPException(403, "Доступ запрещён")
    if data.amount < 1 or data.amount > user["balance"]:
        raise HTTPException(400, "Недостаточно звёзд")
    
    spins = data.extra.get("spins", 1) if data.extra else 1
    total_bet = data.amount * spins
    if total_bet > user["balance"]:
        raise HTTPException(400, "Недостаточно звёзд")
    
    result = play_slots(data.amount, spins)
    
    profit = result["total_profit"]
    if profit >= 0:
        await update_balance(data.user_id, profit, is_win=True)
    else:
        await update_balance(data.user_id, profit)
    
    await add_history(data.user_id, "slots", total_bet, "win" if profit >= 0 else "lose", 0, profit)
    return result

@app.post("/api/upgrade")
async def api_upgrade(data: BetRequest):
    user = await get_user(data.user_id)
    if not user or user["is_banned"]:
        raise HTTPException(403, "Доступ запрещён")
    
    mult = data.extra.get("multiplier", 2) if data.extra else 2
    # For simplicity we use stars as "gift value"
    if data.amount < 10 or data.amount > user["balance"]:
        raise HTTPException(400, "Недостаточно звёзд")
    
    result = play_upgrade(data.amount, mult)
    
    if result["win"]:
        profit = result["new_value"] - data.amount
        await update_balance(data.user_id, profit, is_win=True)
        await add_history(data.user_id, "upgrade", data.amount, "win", mult, profit)
    else:
        await update_balance(data.user_id, -data.amount)
        await add_history(data.user_id, "upgrade", data.amount, "lose", mult, -data.amount)
    
    return result

@app.post("/api/pvp/create")
async def api_pvp_create(data: BetRequest):
    user = await get_user(data.user_id)
    if not user or user["is_banned"]:
        raise HTTPException(403, "Доступ запрещён")
    if data.amount < 10 or data.amount > user["balance"]:
        raise HTTPException(400, "Недостаточно звёзд")
    
    # Reserve bet
    await update_balance(data.user_id, -data.amount)
    room = create_room(data.user_id, data.amount)
    return room

@app.post("/api/pvp/join")
async def api_pvp_join(data: BetRequest):
    user = await get_user(data.user_id)
    if not user or user["is_banned"]:
        raise HTTPException(403, "Доступ запрещён")
    
    room_id = data.extra.get("room_id") if data.extra else None
    if not room_id:
        raise HTTPException(400, "Нет room_id")
    
    room = join_room(room_id, data.user_id)
    if not room:
        raise HTTPException(400, "Комната недоступна")
    
    # Take bet from joiner
    await update_balance(data.user_id, -room["bet"])
    
    # Pay winner
    winner = room["winner_id"]
    payout = room["bet"] * 2
    await update_balance(winner, payout, is_win=True)
    
    await add_history(room["creator_id"], "pvp", room["bet"], "win" if winner == room["creator_id"] else "lose", 2, 
                      room["bet"] if winner == room["creator_id"] else -room["bet"])
    await add_history(data.user_id, "pvp", room["bet"], "win" if winner == data.user_id else "lose", 2,
                      room["bet"] if winner == data.user_id else -room["bet"])
    
    return room

@app.get("/api/pvp/rooms")
async def api_pvp_rooms():
    return get_waiting_rooms()

# Admin endpoints
@app.get("/api/admin/stats")
async def api_admin_stats(user_id: int):
    if user_id != ADMIN_ID:
        raise HTTPException(403, "Только админ")
    return await get_stats()

@app.post("/api/admin/give")
async def api_admin_give(data: dict):
    if data.get("admin_id") != ADMIN_ID:
        raise HTTPException(403, "Только админ")
    ok = await admin_give_stars(data["user_id"], data["amount"])
    return {"success": ok}

@app.post("/api/admin/ban")
async def api_admin_ban(data: dict):
    if data.get("admin_id") != ADMIN_ID:
        raise HTTPException(403, "Только админ")
    await ban_user(data["user_id"], data.get("ban", True))
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

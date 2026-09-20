import random
from typing import List

def generate_mines(grid_size: int = 25, mines_count: int = 3) -> List[int]:
    return random.sample(range(grid_size), mines_count)

def play_mines(bet: int, mines_count: int, revealed: List[int], cashout: bool = False) -> dict:
    if mines_count < 1 or mines_count > 20:
        return {"success": False, "error": "Неверное количество мин"}
    
    grid_size = 25
    mines = generate_mines(grid_size, mines_count)
    
    for pos in revealed:
        if pos in mines:
            return {
                "success": True,
                "win": False,
                "mines": mines,
                "profit": -bet,
                "multiplier": 0
            }
    
    safe_cells = grid_size - mines_count
    if len(revealed) == 0:
        mult = 1.0
    else:
        mult = 1.0
        for i in range(len(revealed)):
            remaining_safe = safe_cells - i
            remaining_total = grid_size - i
            mult *= (remaining_total / remaining_safe) * 0.97
        mult = round(mult, 2)
    
    if cashout or len(revealed) >= safe_cells:
        profit = int(bet * mult) - bet
        return {
            "success": True,
            "win": True,
            "mines": mines,
            "multiplier": mult,
            "profit": profit,
            "payout": bet + profit
        }
    
    return {
        "success": True,
        "win": None,
        "multiplier": mult,
        "mines": None
    }

import random

def generate_crash_point() -> float:
    r = random.random()
    if r < 0.35:
        return round(random.uniform(1.00, 1.40), 2)
    else:
        crash = 0.99 / (1 - random.random() * 0.97)
        crash = min(crash, 50.0)
        return round(max(1.01, crash), 2)

def play_rocket(bet: int, cashout_at: float = None) -> dict:
    crash = generate_crash_point()
    
    if cashout_at is None:
        return {"crash": crash}
    
    if cashout_at <= 1.0:
        return {"success": False, "error": "Множитель должен быть больше 1.0"}
    
    if cashout_at <= crash:
        profit = int(bet * cashout_at) - bet
        return {
            "success": True,
            "win": True,
            "crash": crash,
            "cashout": cashout_at,
            "profit": profit,
            "payout": bet + profit
        }
    else:
        return {
            "success": True,
            "win": False,
            "crash": crash,
            "cashout": cashout_at,
            "profit": -bet,
            "payout": 0
        }

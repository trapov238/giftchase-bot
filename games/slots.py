import random

SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "7️⃣", "💎", "🎁"]
WEIGHTS = [25, 25, 20, 15, 8, 5, 2]

PAYTABLE = {
    ("7️⃣", "7️⃣", "7️⃣"): 50,
    ("💎", "💎", "💎"): 30,
    ("🎁", "🎁", "🎁"): 25,
    ("⭐", "⭐", "⭐"): 15,
    ("🔔", "🔔", "🔔"): 10,
    ("🍋", "🍋", "🍋"): 5,
    ("🍒", "🍒", "🍒"): 3,
}

def spin() -> list:
    return random.choices(SYMBOLS, weights=WEIGHTS, k=3)

def play_slots(bet: int, spins: int = 1) -> dict:
    results = []
    total_profit = 0
    
    for _ in range(spins):
        reels = spin()
        key = tuple(reels)
        mult = PAYTABLE.get(key, 0)
        
        if mult == 0:
            if reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
                mult = 1.2
        
        if mult == 0 and random.random() < 0.25:
            mult = 1.1
        
        profit = int(bet * mult) - bet if mult > 0 else -bet
        total_profit += profit
        
        results.append({
            "reels": reels,
            "multiplier": mult,
            "profit": profit
        })
    
    return {
        "success": True,
        "results": results,
        "total_profit": total_profit,
        "spins": spins
    }

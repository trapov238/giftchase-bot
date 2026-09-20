import random

def play_upgrade(bet_value: int, multiplier: int) -> dict:
    chances = {
        2: 0.70,
        3: 0.55,
        4: 0.40,
        5: 0.30,
        10: 0.15
    }
    
    chance = chances.get(multiplier, 0.3)
    success = random.random() < chance
    
    if success:
        new_value = bet_value * multiplier
        return {
            "success": True,
            "win": True,
            "new_value": new_value,
            "multiplier": multiplier,
            "chance": chance
        }
    else:
        return {
            "success": True,
            "win": False,
            "new_value": 0,
            "multiplier": multiplier,
            "chance": chance
        }

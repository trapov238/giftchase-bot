import random
from typing import Optional

rooms = {}

def create_room(creator_id: int, bet: int) -> dict:
    room_id = random.randint(10000, 99999)
    rooms[room_id] = {
        "id": room_id,
        "creator_id": creator_id,
        "bet": bet,
        "player2_id": None,
        "status": "waiting",
        "winner_id": None
    }
    return rooms[room_id]

def join_room(room_id: int, player_id: int) -> Optional[dict]:
    room = rooms.get(room_id)
    if not room or room["status"] != "waiting" or room["creator_id"] == player_id:
        return None
    
    room["player2_id"] = player_id
    room["status"] = "playing"
    
    if random.random() < 0.5:
        room["winner_id"] = room["creator_id"]
    else:
        room["winner_id"] = player_id
    
    room["status"] = "finished"
    return room

def get_waiting_rooms() -> list:
    return [r for r in rooms.values() if r["status"] == "waiting"]

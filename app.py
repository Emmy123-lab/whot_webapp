from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

SHAPES = ["Circle", "Triangle", "Cross", "Square", "Star"]
NUMBERS = [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14]

game_state = {
    "deck": [],
    "discard_pile": [], # NEW: Tracks cards played so they can be re-shuffled
    "player_hand": [],
    "ai_hand": [],
    "top_card": None,
    "requested_shape": None,
    "message": "GAME STARTED! DROP A MATCHING CARD.",
    "active_penalty": 0,       
    "player_can_play_again": False 
}

def create_deck():
    deck = [{"shape": s, "number": n} for s in SHAPES for n in NUMBERS]
    for _ in range(5):
        deck.append({"shape": "WHOT", "number": 20})
    random.shuffle(deck)
    return deck

def check_and_recycle_deck():
    # If market runs out, grab the history pile, shuffle it sharp, and reset it!
    if len(game_state["deck"]) == 0:
        if len(game_state["discard_pile"]) > 0:
            random.shuffle(game_state["discard_pile"])
            game_state["deck"] = game_state["discard_pile"]
            game_state["discard_pile"] = []
            game_state["message"] += " 🔄 MARKET RE-SHUFFLED!"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_game():
    deck = create_deck()
    player_hand = [deck.pop() for _ in range(6)]
    ai_hand = [deck.pop() for _ in range(6)]
    
    top_card = deck.pop()
    while top_card["shape"] == "WHOT" or top_card["number"] in [1, 2, 14]:
        deck.insert(0, top_card)
        top_card = deck.pop()
        
    game_state.update({
        "deck": deck,
        "discard_pile": [],
        "player_hand": player_hand,
        "ai_hand": ai_hand,
        "top_card": top_card,
        "requested_shape": None,
        "message": "YOUR TURN! DROP A MATCHING CARD.",
        "active_penalty": 0,
        "player_can_play_again": False
    })
    return jsonify(get_clean_state())

def get_clean_state():
    msg = game_state["message"]
    if game_state["requested_shape"]:
        msg += f" (WANTED: {game_state['requested_shape'].upper()})"
    if game_state["active_penalty"] > 0:
        msg += f" ⚠️ PENDING PENALTY: DEFEND OR DRAW {game_state['active_penalty']} CARDS! ⚠️"
    return {
        "player_hand": game_state["player_hand"],
        "ai_hand_size": len(game_state["ai_hand"]),
        "top_card": game_state["top_card"],
        "requested_shape": game_state["requested_shape"],
        "message": msg,
        "market_size": len(game_state["deck"])
    }

@app.route('/play', methods=['POST'])
def play_card():
    data = request.json
    idx = data.get("index")
    req_shape = data.get("requested_shape")
    
    hand = game_state["player_hand"]
    card = hand[idx]
    top = game_state["top_card"]
    req = game_state["requested_shape"]
    penalty = game_state["active_penalty"]
    
    is_valid = False
    if penalty > 0:
        is_valid = (card["number"] == 2)
    else:
        if card["shape"] == "WHOT":
            is_valid = True
        elif req:
            is_valid = (card["shape"] == req)
        else:
            is_valid = (card["shape"] == top["shape"] or card["number"] == top["number"])
        
    if not is_valid:
        return jsonify({"error": "Invalid Move!"}), 400
        
    # Archive old top card to discard history before overriding it
    game_state["discard_pile"].append(game_state["top_card"])
    
    hand.pop(idx)
    game_state["top_card"] = card
    game_state["requested_shape"] = req_shape if card["shape"] == "WHOT" else None
    
    if len(hand) == 0:
        game_state["message"] = "🏆 WHOT CHECK! YOU WON THE MATCH! 🏆"
        return jsonify(get_clean_state())

    game_state["player_can_play_again"] = False
    
    if card["number"] == 1:
        game_state["message"] = "HOLD ON! YOU GET TO PLAY ANOTHER CARD."
        game_state["player_can_play_again"] = True
    elif card["number"] == 2:
        game_state["active_penalty"] += 2
        game_state["message"] = f"YOU PLAYED PICK TWO! PENALTY NOW AT {game_state['active_penalty']}."
    elif card["number"] == 14:
        game_state["message"] = "GENERAL MARKET! AI IS FORCED TO DRAW 1 CARD."
        check_and_recycle_deck()
        if game_state["deck"]:
            game_state["ai_hand"].append(game_state["deck"].pop())
    elif card["shape"] == "WHOT":
        game_state["message"] = f"YOU PLAYED WHOT 20 AND WANTED {req_shape.upper()}."
    else:
        game_state["message"] = f"YOU PLAYED {card['shape'].upper()} {card['number']}."

    return jsonify(get_clean_state())

@app.route('/ai_move', methods=['POST'])
def ai_move():
    if len(game_state["player_hand"]) == 0:
        return jsonify(get_clean_state())
        
    ai_hand = game_state["ai_hand"]
    top = game_state["top_card"]
    req = game_state["requested_shape"]
    penalty = game_state["active_penalty"]
    
    if penalty > 0:
        defenders = [c for c in ai_hand if c["number"] == 2]
        if defenders:
            chosen = defenders[0]
            ai_hand.remove(chosen)
            game_state["discard_pile"].append(game_state["top_card"])
            game_state["top_card"] = chosen
            game_state["active_penalty"] += 2
            game_state["message"] = f"🤖 AI DEFENDED WITH ANOTHER PICK TWO! TOTAL PENALTY IS NOW {game_state['active_penalty']}."
            return jsonify(get_clean_state())
        else:
            for _ in range(penalty):
                check_and_recycle_deck()
                if game_state["deck"]: ai_hand.append(game_state["deck"].pop())
            game_state["active_penalty"] = 0
            game_state["message"] = f"🤖 AI COULD NOT DEFEND! DREW {penalty} CARDS FROM MARKET."
            return jsonify(get_clean_state())

    playable = []
    for c in ai_hand:
        if c["shape"] == "WHOT":
            playable.append(c)
        elif req:
            if c["shape"] == req:
                playable.append(c)
        else:
            if c["shape"] == top["shape"] or c["number"] == top["number"]:
                playable.append(c)
                
    if playable:
        chosen_card = playable[0]
        ai_hand.remove(chosen_card)
        game_state["discard_pile"].append(game_state["top_card"])
        game_state["top_card"] = chosen_card
        game_state["requested_shape"] = None
        
        if chosen_card["number"] == 1:
            game_state["message"] = f"🤖 AI PLAYED {chosen_card['shape'].upper()} 1 (HOLD ON) AND GOES AGAIN!"
            return ai_move()
        elif chosen_card["number"] == 2:
            game_state["active_penalty"] += 2
            game_state["message"] = f"🤖 AI PLAYED PICK TWO! PREPARE TO DEFEND."
        elif chosen_card["number"] == 14:
            game_state["message"] = f"🤖 AI PLAYED {chosen_card['shape'].upper()} 14. GENERAL MARKET! YOU DRAW 1 CARD."
            check_and_recycle_deck()
            if game_state["deck"]: game_state["player_hand"].append(game_state["deck"].pop())
        elif chosen_card["shape"] == "WHOT":
            normal_shapes = [c["shape"] for c in ai_hand if c["shape"] != "WHOT"]
            chosen_req = random.choice(normal_shapes) if normal_shapes else random.choice(SHAPES)
            game_state["requested_shape"] = chosen_req
            game_state["message"] = f"🤖 AI PLAYED WHOT 20 AND REQUESTED {chosen_req.upper()}."
        else:
            game_state["message"] = f"🤖 AI PLAYED {chosen_card['shape'].upper()} {chosen_card['number']}."
    else:
        check_and_recycle_deck()
        if game_state["deck"]:
            ai_hand.append(game_state["deck"].pop())
            game_state["message"] = "🤖 AI HAD NO MATCH AND WENT TO MARKET."
            
    if len(ai_hand) == 0:
        game_state["message"] = "😭 GAME OVER! AI CALLED WHOT CHECK AND WON! 😭"
        
    return jsonify(get_clean_state())

@app.route('/market', methods=['POST'])
def market_draw():
    penalty = game_state["active_penalty"]
    
    if penalty > 0:
        for _ in range(penalty):
            check_and_recycle_deck()
            if game_state["deck"]: game_state["player_hand"].append(game_state["deck"].pop())
        game_state["active_penalty"] = 0
        game_state["message"] = f"YOU ACCEPTED PENALTY AND DREW {penalty} CARDS."
    else:
        check_and_recycle_deck()
        if game_state["deck"]:
            card = game_state["deck"].pop()
            game_state["player_hand"].append(card)
            game_state["message"] = "YOU WENT TO MARKET AND DREW A CARD."
            
    return jsonify(get_clean_state())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

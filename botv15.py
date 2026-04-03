#!/usr/bin/env python3  
# ==============================================  
# IM2015 SMART BOT v15.7 (AUTO-SERIAL DETECT)
# MODES: SERIAL DIVISION + MINUTE WEIGHTING + TREND
# ==============================================  

import requests  
import time  
from datetime import datetime, timedelta  
import os  
import random  
from collections import deque  

# === CONFIG ===  
API_URL = "https://manage.im2015.com/api/game/guess_odd?limit=50"  
TELEGRAM_TOKEN = "7905271612:AAFFm7oUCDpv8mSrYl7B-_D4Ez5i4QHVn1g"  
CHAT_ID_FILE = "chat_id.txt"  
LOG_FILE = "bet_history.csv"

# === SETTINGS ===  
BET_STRATEGY = [10, 30, 70, 150, 350, 800]  
CHECK_INTERVAL = 5  # Bawat 5 seconds titingin sa API kung nagbago ang serial

# === GLOBALS ===  
last_serial = None  
last_prediction = None  
current_bet_index = 0
drop_list = deque(maxlen=10)  
cached_chat_id = None  

# ============================================================  
# PREDICTION ENGINE
# ============================================================  

def generate_prediction(serial, current_number):
    try:
        r = requests.get(API_URL, timeout=5).json()
        history_data = r.get("data", [])
        history_numbers = [int(x.get("number", 0)) for x in history_data]
        
        odds = sum(1 for n in history_numbers if n % 2 != 0)
        evens = sum(1 for n in history_numbers if n % 2 == 0)
        
        serial_str = str(serial)
        val = float(serial_str[:3] + "." + serial_str[3:]) if len(serial_str) > 3 else float(serial)
        div_result = val / current_number if current_number != 0 else val
        digits = ''.join(filter(str.isdigit, f"{div_result:.10f}"))
        base_pred = int(digits[-2]) if len(digits) >= 2 else random.randint(0, 9)

        # Minute Analysis
        current_min = datetime.now().minute
        if current_min % 2 == 0:
            prediction = base_pred if base_pred % 2 == 0 else (base_pred + 1) % 10
        else:
            prediction = base_pred if base_pred % 2 != 0 else (base_pred + 1) % 10

        return prediction
    except:
        return random.randint(0, 9)

# ============================================================  
# UTILS & TELEGRAM
# ============================================================  

def get_chat_id():
    global cached_chat_id
    if cached_chat_id: return cached_chat_id
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE, "r") as f:
            cached_chat_id = f.read().strip()
            return cached_chat_id
    return None

def send_telegram(text):
    cid = get_chat_id()
    if not cid: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": cid, "text": text, "parse_mode": "HTML"}, timeout=10)
    except: pass

def fetch_data():
    try:
        r = requests.get(API_URL, timeout=10).json()
        latest = r.get("data", [])[0]
        return latest.get("serial"), int(latest.get("number", 0))
    except: return None

# ============================================================  
# MAIN AUTOMATION LOOP
# ============================================================  

def main():
    global last_serial, last_prediction, current_bet_index
    print("🔥 IM2015 SERIAL MONITOR ACTIVE")
    
    # Paunang bati para malaman kung online ang bot
    if get_chat_id():
        send_telegram("🚀 <b>Bot is now Monitoring...</b>\nAutomatic chat enabled on serial change.")

    while True:
        try:
            result = fetch_data()
            if not result:
                time.sleep(CHECK_INTERVAL)
                continue

            serial, number = result

            # DITO ANG AUTOMATIC TRIGGER: Kapag ang serial ay hindi na pareho sa huling record
            if serial != last_serial:
                
                # 1. Evaluate kung nanalo ba yung huling prediction bago mag-update
                res_status = ""
                if last_prediction is not None:
                    is_win = (last_prediction % 2 == number % 2)
                    if is_win:
                        res_status = "✅ WIN"
                        current_bet_index = 0 
                    else:
                        res_status = "❌ LOSS"
                        current_bet_index = min(current_bet_index + 1, len(BET_STRATEGY) - 1)
                    
                    drop_list.appendleft(f"{last_prediction} {res_status}")

                # 2. Generate Prediction para sa BAGONG serial
                last_serial = serial
                bet_amount = BET_STRATEGY[current_bet_index]
                last_prediction = generate_prediction(serial, number)
                
                now = datetime.now() # Philippine Time (if server is PH)
                history = "\n".join(drop_list)

                # 3. AUTOMATIC CHAT/SEND
                msg = (
                    f"📢 <b>NEW SERIAL DETECTED</b>\n\n"
                    f"⏰ {now:%I:%M:%S %p}\n"
                    f"🔢 Serial: <code>{serial}</code>\n"
                    f"🎲 Last Result: <b>{number}</b>\n"
                    f"💰 Next Bet: <b>{bet_amount}</b>\n"
                    f"🎯 Next Pred: <code>{last_prediction}</code>\n\n"
                    f"📊 <b>Drop History:</b>\n{history if history else 'Analyzing...'}"
                )
                
                send_telegram(msg)
                print(f"[{now:%H:%M:%S}] New Serial: {serial} | Sent to Telegram.")

            # Mag-antay ng 5 seconds bago tumingin ulit sa API
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityTextUrl
import re
import asyncio
from datetime import datetime
import os

# ----------------------------------------------------------------
# API and User Configuration
# ----------------------------------------------------------------
api_id = API_ID
api_hash = 'API_HASH'
phone_number =  "+351 123 456 789"  # Your phone number with country code
# Group and Bot details
group_id = 2411228501
bot_username = 'CashCash_trade_bot'

# Initialize Telegram client session
client = TelegramClient('session_name', api_id, api_hash)

# ----------------------------------------------------------------
# File to store purchased CAs
# ----------------------------------------------------------------
PURCHASED_CAS_FILE = "purchased_cas.txt"
purchased_cas = set()

# ----------------------------------------------------------------
# Queue to manage pending CAs
# ----------------------------------------------------------------
ca_queue = asyncio.Queue()

# ----------------------------------------------------------------
# Set to track pending CAs
# ----------------------------------------------------------------
pending_cas = set()

# ----------------------------------------------------------------
# Lock to synchronize file access
# ----------------------------------------------------------------
file_lock = asyncio.Lock()

# ----------------------------------------------------------------
# Set to store processed message IDs (to prevent double handling)
# ----------------------------------------------------------------
processed_messages = set()

# ----------------------------------------------------------------
# Load purchased CAs from file
# ----------------------------------------------------------------
def load_purchased_cas():
    if os.path.exists(PURCHASED_CAS_FILE):
        with open(PURCHASED_CAS_FILE, 'r') as f:
            for line in f:
                ca = line.strip()
                if ca:
                    purchased_cas.add(ca)
        print(f"[INFO] {len(purchased_cas)} purchased CAs loaded from '{PURCHASED_CAS_FILE}'.")
    else:
        with open(PURCHASED_CAS_FILE, 'w') as f:
            pass
        print(f"[INFO] File '{PURCHASED_CAS_FILE}' created to store purchased CAs.")

# ----------------------------------------------------------------
# Save a purchased CA to file
# ----------------------------------------------------------------
async def save_purchased_ca(ca):
    async with file_lock:
        with open(PURCHASED_CAS_FILE, 'a') as f:
            f.write(f"{ca}\n")
    print(f"[INFO] CA '{ca}' saved to '{PURCHASED_CAS_FILE}'.")

# ----------------------------------------------------------------
# Send /start ca_<hash> to Bot B
# ----------------------------------------------------------------
async def send_to_bot(ca):
    command = f"/start ca_{ca}"
    print(f"[DEBUG] Sending command to @{bot_username}: {command}")
    await client.send_message(bot_username, command)
    print(f"[INFO] CA '{ca}' sent to bot @{bot_username}")

# ----------------------------------------------------------------
# Click the inline button that contains 'Buy 0.1 SOL'
# ----------------------------------------------------------------
async def click_buy_0_25_sol_button(event):
    """
    Iterates over inline buttons in the message:
    - Searches for a button whose text contains 'Buy 0.1 SOL'.
    - Clicks that button if found, then returns True immediately.
    """
    if event.buttons:
        print(f"[DEBUG] Bot message has {len(event.buttons)} row(s) of buttons.")
        for i, row in enumerate(event.buttons, start=0):    # zero-based index for event.click
            for j, button in enumerate(row, start=0):
                text_btn = getattr(button, 'text', '')
                if 'Buy 0.1 SOL' in text_btn:
                    print(f"[INFO] Found button with text '{text_btn}'. Clicking...")
                    try:
                        await event.click(i, j)
                        print("[INFO] Button 'Buy 0.10 SOL' clicked successfully!")
                        return True  # STOP searching further
                    except Exception as e:
                        print(f"[ERROR] Failed to click the button: {e}")
                        return False
                else:
                    print(f"    [DEBUG] Button col {j+1}: '{text_btn}' does not match.")
        print("[WARN] No button containing 'Buy 0.10 SOL' was found.")
    else:
        print("[DEBUG] Bot message has no buttons.")
    return False

# ----------------------------------------------------------------
# Click the 'Try Again' button if it exists
# ----------------------------------------------------------------
async def click_try_again_button(event):
    """
    Searches for a button containing 'Try Again' (or similar) in its text.
    Clicks on it if found, then returns True if successfully clicked.
    """
    if event.buttons:
        print(f"[DEBUG] Checking for 'Try Again' button. Found {len(event.buttons)} row(s) of buttons.")
        for i, row in enumerate(event.buttons, start=0):
            for j, button in enumerate(row, start=0):
                text_btn = getattr(button, 'text', '')
                if 'Try Again' in text_btn:
                    print(f"[INFO] Found 'Try Again' button: '{text_btn}'. Clicking...")
                    try:
                        await event.click(i, j)
                        print("[INFO] 'Try Again' button clicked!")
                        return True
                    except Exception as e:
                        print(f"[ERROR] Failed to click 'Try Again': {e}")
                        return False
                else:
                    print(f"    [DEBUG] Button col {j+1}: '{text_btn}' is not 'Try Again'.")
        print("[WARN] No button containing 'Try Again' was found.")
    else:
        print("[DEBUG] No buttons in this message to check for 'Try Again'.")
    return False

# ----------------------------------------------------------------
# Handler: Group messages (where the CA + Price appear)
# ----------------------------------------------------------------
@client.on(events.NewMessage(chats=group_id))
async def monitor_messages(event):
    message_text = event.raw_text
    print(f"[DEBUG] New message in group {group_id} - ID={event.id} - Time={datetime.now()}")
    print("[DEBUG] Message text (raw_text):")
    print(message_text)

    # 1) Extract prices ($0.xxxx) including the format $0.{3}283 => 0.000283
    pattern = r'\$0\.(?:\{(\d+)\})?(\d+)'
    matches = re.findall(pattern, message_text)

    if matches:
        parsed_prices = []
        for zero_count, digits in matches:
            if zero_count:  # e.g. $0.{3}283 => 0.000283
                constructed_price_str = "0." + ("0" * int(zero_count)) + digits
            else:
                constructed_price_str = "0." + digits

            try:
                parsed_prices.append(float(constructed_price_str))
            except ValueError:
                pass

        if parsed_prices:
            min_avg_price = min(parsed_prices)
            print(f"[DEBUG] min_avg_price = {min_avg_price}")
        else:
            min_avg_price = None
            print("[WARN] Could not parse any valid float from matched prices.")
    else:
        min_avg_price = None
        print("[WARN] No price found in the message.")

    # 2) Tentamos extrair apenas UM CA válido por mensagem
    found_and_sent = False  # Marca se já enviamos /start para não repetir

    if event.message and event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                url_real = entity.url
                print(f"[DEBUG] Embedded URL: {url_real}")

                # Tenta capturar '?start=ca_xxx' ou 'dexscreener.com/solana/xxx'
                ca_match = re.search(r'start=ca_([^)\s]+)', url_real)
                if not ca_match:
                    ca_match = re.search(r'dexscreener\.com/solana/([^)\s]+)', url_real)

                if ca_match and not found_and_sent:  # Se ainda não enviamos nada nesta msg
                    ca_val = ca_match.group(1)
                    print(f"[INFO] Found CA: {ca_val}")

                    if min_avg_price is not None and 0.00035 <= min_avg_price <= 0.15:
                        print("[INFO] Price is within range (0.00035 - 0.15). Sending /start ca_...")
                        await send_to_bot(ca_val)
                        await ca_queue.put(ca_val)
                        pending_cas.add(ca_val)
                        found_and_sent = True
                        print(f"[DEBUG] CA '{ca_val}' added to the queue and marked as pending.")
                        # IMPORTANT: Enviamos apenas 1 CA por mensagem
                        break
                    else:
                        if min_avg_price is not None:
                            print(f"[INFO] min_avg_price = {min_avg_price} out of range (0.00035 - 0.15). Not buying.")
                        else:
                            print("[INFO] No min_avg_price found. Not buying.")
    else:
        print("[DEBUG] No CA extracted from entities in this message.")

# ----------------------------------------------------------------
# Handler: Messages from Bot B (bot_username)
# ----------------------------------------------------------------
@client.on(events.NewMessage(from_users=bot_username))
async def handle_bot_responses(event):
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[DEBUG] ======================")
    print(f"[DEBUG] New message from Bot B @{bot_username} at {now_str}")
    print(f"[DEBUG] Message ID: {event.id}")
    print(f"[DEBUG] Sender ID: {event.sender_id}")
    print(f"[DEBUG] Message text:\n{event.raw_text}")

    # 1) Evitar processar a mesma mensagem mais de uma vez
    if event.id in processed_messages:
        print(f"[INFO] Message ID {event.id} has already been processed. Skipping.")
        return
    processed_messages.add(event.id)

    # 2) Verificar se houve erro de BuyTransaction
    fail_marker = "BuyTransaction Fail"
    if fail_marker in event.raw_text:
        print("[WARN] The bot indicates a BuyTransaction Fail. Attempting 'Try Again'...")

        # a) Tentar clicar no botão "Try Again"
        await click_try_again_button(event)

        # b) Tentar novamente "Buy 0.10 SOL"
        print("[INFO] Attempting to buy 0.10 SOL again (ignoring purchased status).")
        await click_buy_0_25_sol_button(event)
        return

    # 3) Caso normal: processar a fila de CA
    if ca_queue.empty():
        print("[WARN] No pending CA for this bot response.")
        return

    # 4) Obter CA da fila
    try:
        ca = await ca_queue.get()
        print(f"[DEBUG] CA '{ca}' retrieved from the queue for processing.")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve CA from the queue: {e}")
        return

    # 5) Tentar clicar no botão "Buy 0.10 SOL"
    buy_success = await click_buy_0_25_sol_button(event)

    if buy_success:
        # Marcar como comprado
        purchased_cas.add(ca)
        await save_purchased_ca(ca)
        pending_cas.discard(ca)
    else:
        print(f"[ERROR] Failed to click 'Buy 0.10 SOL' for CA '{ca}'.")
        # Opcional: Recolocar na fila se quiser tentar em mensagem futura
        # await ca_queue.put(ca)

# ----------------------------------------------------------------
# Main function
# ----------------------------------------------------------------
async def main():
    load_purchased_cas()
    print("[DEBUG] Starting Telethon session...")
    await client.start(phone=phone_number)
    print("[INFO] UserBot is now connected and running...")
    print("[DEBUG] Listening for messages... (Press Ctrl+C to stop)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

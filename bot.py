from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityTextUrl
import re
import asyncio
from datetime import datetime
import os

# ----------------------------------------------------------------
# API and User Configuration
# ----------------------------------------------------------------
api_id = VALOR_DA_API_ID
api_hash = VALOR_DA_API_HASH
phone_number = '+351 O_TEU_NUMERO'

# Group and Bot details
group_id = 4639774418
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
        # Create the file if it does not exist
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
# Click the inline button that contains 'Buy 0.25 SOL'
# ----------------------------------------------------------------
async def click_buy_0_25_sol_button(event):
    """
    Iterates over inline buttons in the message:
    - Searches for a button whose text contains 'Buy 0.25 SOL'.
    - Clicks that button if found.
    """
    if event.buttons:
        print(f"[DEBUG] Bot message has {len(event.buttons)} row(s) of buttons.")
        for i, row in enumerate(event.buttons, start=1):
            for j, button in enumerate(row, start=1):
                text_btn = getattr(button, 'text', '')
                if 'Buy 0.25 SOL' in text_btn:
                    print(f"[INFO] Found button with text '{text_btn}'. Clicking...")
                    try:
                        await event.click(i - 1, j - 1)  # zero-based indexing
                        print("[INFO] Button clicked successfully!")
                        return True
                    except Exception as e:
                        print(f"[ERROR] Failed to click the button: {e}")
                        return False
                else:
                    print(f"    [DEBUG] Button col {j}: '{text_btn}' does not match.")
        print("[WARN] No button containing 'Buy 0.25 SOL' was found.")
    else:
        print("[DEBUG] Bot message has no buttons.")
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
    #    Then determine min_avg_price
    pattern = r'\$0\.(?:\{(\d+)\})?(\d+)'  # captures optional braces {n} for zeros + trailing digits
    matches = re.findall(pattern, message_text)

    if matches:
        parsed_prices = []
        for zero_count, digits in matches:
            if zero_count:  # e.g. $0.{3}283
                constructed_price_str = "0." + ("0" * int(zero_count)) + digits
            else:  # e.g. $0.0022 (no braces)
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

    # 2) Attempt to extract CA from embedded links (start=ca_... or /solana/...)
    found_ca = False
    if event.message and event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                url_real = entity.url
                print(f"[DEBUG] Embedded URL: {url_real}")

                # Try to capture '?start=ca_xxx' or 'dexscreener.com/solana/xxx'
                ca_match = re.search(r'start=ca_([^)\s]+)', url_real)
                if not ca_match:
                    ca_match = re.search(r'dexscreener\.com/solana/([^)\s]+)', url_real)

                if ca_match:
                    ca_val = ca_match.group(1)
                    print(f"[INFO] Found CA: {ca_val}")
                    found_ca = True

                    # Check if CA was already purchased or is pending
                    if ca_val in purchased_cas:
                        print(f"[INFO] CA '{ca_val}' is already purchased. Ignoring.")
                        continue
                    if ca_val in pending_cas:
                        print(f"[INFO] CA '{ca_val}' is already pending. Ignoring.")
                        continue

                    # Check if the min_avg_price is within the desired range
                    if min_avg_price is not None and 0.00035 <= min_avg_price <= 0.15:
                        print("[INFO] Price is within the range (0.00035 - 0.15). Sending /start ca_...")
                        await send_to_bot(ca_val)
                        await ca_queue.put(ca_val)
                        pending_cas.add(ca_val)
                        print(f"[DEBUG] CA '{ca_val}' added to the queue and marked as pending.")
                    else:
                        if min_avg_price is not None:
                            print(f"[INFO] min_avg_price = {min_avg_price} is out of the allowed range (0.00035 - 0.15). Not buying.")
                        else:
                            print("[INFO] No min_avg_price found. Not buying.")

    if not found_ca:
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

    # Check if there are any pending CAs
    if ca_queue.empty():
        print("[WARN] No pending CA for this bot response.")
        return

    # Retrieve the next CA from the queue
    try:
        ca = await ca_queue.get()
        print(f"[DEBUG] CA '{ca}' retrieved from the queue for processing.")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve CA from the queue: {e}")
        return

    # Attempt to click the buy button
    buy_success = await click_buy_0_25_sol_button(event)

    if buy_success:
        # Mark this CA as purchased and save to file
        purchased_cas.add(ca)
        await save_purchased_ca(ca)
        # Remove from pending set
        pending_cas.discard(ca)
    else:
        print(f"[ERROR] Failed to click the 'Buy 0.25 SOL' button for CA '{ca}'.")
        # Optionally, re-queue the CA to try again
        # await ca_queue.put(ca)


# ----------------------------------------------------------------
# Main function
# ----------------------------------------------------------------
async def main():
    # Load purchased CAs from file
    load_purchased_cas()

    print("[DEBUG] Starting Telethon session...")
    await client.start(phone=phone_number)
    print("[INFO] UserBot is now connected and running...")
    print("[DEBUG] Listening for messages... (Press Ctrl+C to stop)")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())

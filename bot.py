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
# Load purchased CAs from file (at startup)
# ----------------------------------------------------------------
def load_purchased_cas():
    """Load from file the CAs that were already purchased."""
    if os.path.exists(PURCHASED_CAS_FILE):
        with open(PURCHASED_CAS_FILE, 'r') as f:
            for line in f:
                ca = line.strip()
                if ca:
                    purchased_cas.add(ca)
        print(f"[INFO] Loaded {len(purchased_cas)} purchased CAs from '{PURCHASED_CAS_FILE}'.")
    else:
        # Create an empty file to ensure it exists
        with open(PURCHASED_CAS_FILE, 'w') as f:
            pass
        print(f"[INFO] Created empty file '{PURCHASED_CAS_FILE}'.")

# ----------------------------------------------------------------
# Save a purchased CA to file
# ----------------------------------------------------------------
async def save_purchased_ca(ca: str):
    """Save the purchased CA in a file (append mode)."""
    async with file_lock:
        with open(PURCHASED_CAS_FILE, 'a') as f:
            f.write(f"{ca}\n")
    print(f"[INFO] -> CA '{ca}' saved to '{PURCHASED_CAS_FILE}'.")

# ----------------------------------------------------------------
# Send /start ca_<hash> to Bot B
# ----------------------------------------------------------------
async def send_to_bot(ca: str):
    """Send the /start ca_<hash> command to the target bot."""
    command = f"/start ca_{ca}"
    print(f"[INFO] -> Sending /start for CA '{ca}' to @{bot_username}...")
    await client.send_message(bot_username, command)

# ----------------------------------------------------------------
# Click the inline button that contains 'Buy 0.1 SOL'
# ----------------------------------------------------------------
async def click_buy_0_1_sol_button(event) -> bool:
    """
    Tenta encontrar um botão 'Buy 0.1 SOL' na mensagem.
    Retorna True se clicou com sucesso; False caso contrário.
    """
    if not event.buttons:
        return False

    for i, row in enumerate(event.buttons):
        for j, button in enumerate(row):
            text_btn = getattr(button, 'text', '')
            if 'Buy 0.1 SOL' in text_btn:
                try:
                    await event.click(i, j)
                    print("[INFO] -> Button 'Buy 0.1 SOL' clicked successfully.")
                    return True
                except Exception as e:
                    print(f"[ERROR] Failed to click 'Buy 0.1 SOL': {e}")
                    return False
    return False

# ----------------------------------------------------------------
# Click the 'Try Again' button if it exists
# ----------------------------------------------------------------
async def click_try_again_button(event) -> bool:
    """
    Se a mensagem possuir um botão "Try Again", clica nele e retorna True.
    Caso não encontre, retorna False.
    """
    if not event.buttons:
        return False

    for i, row in enumerate(event.buttons):
        for j, button in enumerate(row):
            text_btn = getattr(button, 'text', '')
            if 'Try Again' in text_btn:
                try:
                    await event.click(i, j)
                    print("[INFO] -> 'Try Again' button clicked.")
                    return True
                except Exception as e:
                    print(f"[ERROR] Failed to click 'Try Again': {e}")
                    return False
    return False

# ----------------------------------------------------------------
# Handler: Group messages
#   - Procuramos um preço e um CA
# ----------------------------------------------------------------
@client.on(events.NewMessage(chats=group_id))
async def monitor_group_messages(event):
    message_id = event.id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = event.raw_text

    print(f"\n[GROUP] Message #{message_id} @ {timestamp}")
    # 1) Extrair o menor preço
    pattern = r'\$0\.(?:\{(\d+)\})?(\d+)'
    matches = re.findall(pattern, text)
    min_avg_price = None

    if matches:
        prices = []
        for zero_count, digits in matches:
            # e.g. $0.{3}123 => 0.000123
            prefix = "0." + ("0" * int(zero_count)) if zero_count else "0."
            try:
                prices.append(float(prefix + digits))
            except ValueError:
                pass
        if prices:
            min_avg_price = min(prices)

    if min_avg_price is not None:
        print(f"[INFO] -> Detected price: {min_avg_price:.8f}")
    else:
        print("[INFO] -> No valid price found in this message.")

    # Processar um único CA por mensagem
    found_and_sent = False

    # 2) Tentar extrair CA das entidades de link
    if event.message and event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                url = entity.url
                # Checar no padrão ?start=ca_...
                ca_match = re.search(r'start=ca_([^)\s]+)', url)
                # Se não encontrar, checar dexscreener
                if not ca_match:
                    ca_match = re.search(r'dexscreener\.com/solana/([^)\s]+)', url)

                if ca_match and not found_and_sent:
                    ca_val = ca_match.group(1)
                    print(f"[INFO] -> Found CA: {ca_val}")

                    # Se já está em purchased_cas, ignoramos
                    if ca_val in purchased_cas:
                        print(f"[INFO] -> CA '{ca_val}' já comprado anteriormente. Ignorando.")
                        continue

                    # 3) Verificar se está no range de preço e comprar
                    if min_avg_price and 0.00035 <= min_avg_price <= 0.01:
                        print(f"[INFO] -> Price {min_avg_price:.8f} está no range (0.00035 - 0.01). Comprando...")
                        await send_to_bot(ca_val)
                        await ca_queue.put(ca_val)
                        pending_cas.add(ca_val)
                        found_and_sent = True
                    else:
                        print(f"[INFO] -> Price {min_avg_price} fora do range ou não encontrado. Não compra.")

                    # Enviamos apenas 1 CA
                    if found_and_sent:
                        break

# ----------------------------------------------------------------
# Handler: Bot messages
#   - Observamos respostas do bot para clicar em "Buy 0.1 SOL", etc.
# ----------------------------------------------------------------
@client.on(events.NewMessage(from_users=bot_username))
async def handle_bot_messages(event):
    message_id = event.id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = event.raw_text

    print(f"\n[BOT] Message #{message_id} @ {timestamp}")

    # Evitar processar 2x a mesma mensagem
    if message_id in processed_messages:
        print("[INFO] -> This bot message was already processed. Skipping.")
        return
    processed_messages.add(message_id)

    # Se detectarmos a mensagem de falha on-chain:
    #   ❌BuyTransaction Fail
    #   ...
    #   [ Try Again ]
    if "BuyTransaction Fail" in text:
        print("[WARN] -> Bot indicated a 'BuyTransaction Fail'... clicando Try Again e comprando de novo.")
        # 1) Clicar no botão "Try Again"
        success = await click_try_again_button(event)
        # 2) Se clicou, agora deve vir uma nova mensagem "normal" do bot
        #    Assim que chegar, iremos novamente apertar "Buy 0.1 SOL" (lá embaixo)
        #    **ou** já existe o botão no mesmo event. Se estiver no mesmo event, então:
        if success:
            print("[INFO] -> Attempting to buy again (0.1 SOL)...")
            await click_buy_0_1_sol_button(event)
        return

    # Se não há CA na fila, não temos o que fazer
    if ca_queue.empty():
        print("[INFO] -> No pending CA in queue for this message.")
        return

    # Retiramos o CA da fila para tentar comprar
    try:
        ca = await ca_queue.get()
    except Exception as e:
        print(f"[ERROR] -> Failed to get CA from queue: {e}")
        return

    print(f"[INFO] -> Processing CA: {ca}")
    buy_success = await click_buy_0_1_sol_button(event)

    if buy_success:
        # **Atenção**: buy_success aqui significa apenas que conseguimos "clicar no botão".
        # Se a transação falhar on-chain, virá novamente "BuyTransaction Fail" em outra mensagem,
        # e faremos o reprocessamento. Só confirmamos no final que não veio fail.
        purchased_cas.add(ca)
        await save_purchased_ca(ca)
        pending_cas.discard(ca)
        print(f"[INFO] -> CA '{ca}' purchase flow completed (click).")
    else:
        print(f"[ERROR] -> Failed to click 'Buy 0.1 SOL' for CA '{ca}'.")
        # Se quiser, re-insira na fila para tentar de novo
        # await ca_queue.put(ca)

# ----------------------------------------------------------------
# Main function
# ----------------------------------------------------------------
async def main():
    load_purchased_cas()
    print("[INFO] Starting the Telegram Client session...")
    await client.start(phone=phone_number)
    print("[INFO] Bot is now connected and listening. (Ctrl + C to stop)")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

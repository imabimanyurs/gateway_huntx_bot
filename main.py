
import requests
import asyncio
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from collections import defaultdict
from datetime import datetime, timedelta
import time

BOT_TOKEN = "8126996237:AAFBKH7e7AZaVCEkALdpOuTOK3pZbJoD3f0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Rate limiting
RATE_LIMIT = 5  # requests per minute
user_requests = defaultdict(list)

PAYMENT_GATEWAYS = [
    "razorpay.com", "payu.in", "ccavenue.com", "instamojo.com", "cashfree.com",
    "paytm.com", "billdesk.com", "paypal.com", "stripe.com", "authorize.net", 
    "squareup.com", "alipay.com", "payoneer.com", "amazonpay.com", "bitpay.com", 
    "crypto.com/pay"
]

def is_rate_limited(user_id: int) -> bool:
    current_time = datetime.now()
    user_requests[user_id] = [t for t in user_requests[user_id] 
                             if current_time - t < timedelta(minutes=1)]
    
    if len(user_requests[user_id]) >= RATE_LIMIT:
        return True
    
    user_requests[user_id].append(current_time)
    return False

def clean_url(input_text: str) -> str:
    url = input_text.strip().replace(" ", "")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def find_payment_gateways(url: str) -> dict:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers, verify=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        found_gateways = [gateway for gateway in PAYMENT_GATEWAYS 
                         if gateway in response.text]

        return {
            "status": response.status_code,
            "gateways": found_gateways if found_gateways else ["⚠️ No payment gateway detected"],
            "server": response.headers.get("Server", "Unknown")
        }

    except requests.exceptions.SSLError:
        return {"status": "Error", "error": "❌ SSL Certificate verification failed"}
    except requests.exceptions.ConnectionError:
        return {"status": "Error", "error": "❌ Failed to connect to the server"}
    except requests.exceptions.Timeout:
        return {"status": "Error", "error": "❌ Request timed out"}
    except requests.exceptions.RequestException as e:
        return {"status": "Error", "error": f"❌ Error: {str(e)}"}

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.reply(
        "👋 Welcome! Send me a website URL to scan for payment gateways."
    )

@dp.message()
async def process_url(message: Message):
    if is_rate_limited(message.from_user.id):
        await message.reply("⚠️ Rate limit exceeded. Please wait a minute.")
        return

    try:
        url = clean_url(message.text)
        status_message = await message.reply("🔍 Scanning website... Please wait!")

        result = find_payment_gateways(url)

        if "error" in result:
            await status_message.edit_text(f"❌ Error: {result['error']}")
            return

        response_text = (
            f"🟢 **URL:** {url}\n"
            f"🎉 **Status:** {result['status']}\n"
            f"🗿 **Gateway:** {', '.join(result['gateways'])}\n"
            f"🌐 **Server:** {result['server']}\n"
        )

        await status_message.edit_text(response_text, parse_mode="Markdown")

    except Exception as e:
        await message.reply(f"❌ An unexpected error occurred: {str(e)}")

async def main():
    print("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

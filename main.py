import os
import time
import requests
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from collections import defaultdict
from datetime import datetime, timedelta

# Load environment variables from Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
BUILTWITH_API_KEY = os.getenv("BUILTWITH_API_KEY")

if not BOT_TOKEN or not BUILTWITH_API_KEY:
    raise ValueError("❌ Missing environment variables! Set BOT_TOKEN and BUILTWITH_API_KEY in Railway.")

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Rate limiting (5 requests per minute per user)
RATE_LIMIT = 5
user_requests = defaultdict(list)

# List of known payment gateways (Updated & Expanded)
PAYMENT_GATEWAYS = [
    # Global Providers
    "paypal.com", "stripe.com", "paddle.com", "fastspring.com", "worldpay.com",
    "adyen.com", "checkout.com", "authorize.net", "squareup.com", "payflow.com",
    "braintreepayments.com", "skrill.com", "2checkout.com", "bluesnap.com", "klarna.com",
    
    # India-Focused Gateways
    "razorpay.com", "payu.in", "ccavenue.com", "instamojo.com", "cashfree.com",
    "paytm.com", "billdesk.com",

    # Regional Providers
    "eway.com.au", "amazonpay.com", "alipay.com", "wepay.com",
    "shopify.com", "shopify-payments.com",

    # Crypto Payment Gateways
    "bitpay.com", "commerce.coinbase.com", "coingate.com", "nowpayments.io", "crypto.com/pay"
]

# Function to check rate limits
def is_rate_limited(user_id: int) -> bool:
    current_time = datetime.now()
    user_requests[user_id] = [t for t in user_requests[user_id] 
                             if current_time - t < timedelta(minutes=1)]
    
    if len(user_requests[user_id]) >= RATE_LIMIT:
        return True
    
    user_requests[user_id].append(current_time)
    return False

# Function to clean and format URL
def clean_url(input_text: str) -> str:
    url = input_text.strip().replace(" ", "")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

# Function to check if Cloudflare is present
def detect_cloudflare(headers):
    return "True ✅" if "cf-ray" in headers or "cloudflare" in headers.get("Server", "").lower() else "False ❌"

# Function to detect Captcha
def detect_captcha(html):
    return "Yes ⚠️" if "captcha" in html.lower() or "recaptcha" in html.lower() else "No ❌"

# Function to detect Authentication Requirement
def detect_auth(html):
    return "Yes 🔥" if "login" in html.lower() or "signin" in html.lower() else "No ❌"

# Function to detect Verified by Visa (VBV)
def detect_vbv(html):
    return "True ✅" if "verified by visa" in html.lower() or "3dsecure" in html.lower() else "False ❌"

# Function to get site platform using BuiltWith API
def detect_platform(url):
    try:
        builtwith_url = f"https://api.builtwith.com/v20/api.json?KEY={BUILTWITH_API_KEY}&LOOKUP={url}"
        response = requests.get(builtwith_url, timeout=10)
        data = response.json()
        technologies = [tech['Name'] for tech in data.get('Results', [{}])[0].get('Technologies', [])]
        return ", ".join(technologies) if technologies else "Unknown"
    except:
        return "Unknown"

# Function to get fully rendered HTML using Playwright (for JS-loaded content)
async def fetch_js_rendered_page(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000)  # 30s timeout
        content = await page.content()
        await browser.close()
        return content

# Function to find payment gateways
async def find_payment_gateways(url: str) -> dict:
    try:
        start_time = time.time()
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=10, headers=headers, verify=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        found_gateways = [gateway for gateway in PAYMENT_GATEWAYS if gateway in response.text]

        # If no gateways found, use Playwright for JavaScript-loaded content
        if not found_gateways:
            rendered_html = await fetch_js_rendered_page(url)
            found_gateways = [gateway for gateway in PAYMENT_GATEWAYS if gateway in rendered_html]

        time_taken = round(time.time() - start_time, 2)

        return {
            "status": response.status_code,
            "gateways": found_gateways if found_gateways else ["⚠️ No payment gateway detected"],
            "server": response.headers.get("Server", "Unknown"),
            "captcha": detect_captcha(response.text),
            "cloudflare": detect_cloudflare(response.headers),
            "platform": detect_platform(url),
            "auth_required": detect_auth(response.text),
            "vbv": detect_vbv(response.text),
            "time_taken": f"{time_taken}s"
        }

    except requests.exceptions.RequestException as e:
        return {"status": "Error", "error": f"❌ Error: {str(e)}"}

# Telegram bot handler
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.reply("👋 Send a URL, and I'll scan for payment gateways & platform details.")

@dp.message()
async def process_url(message: Message):
    if is_rate_limited(message.from_user.id):
        await message.reply("⚠️ Rate limit exceeded. Please wait a minute.")
        return

    url = clean_url(message.text)
    status_message = await message.reply("🔍 Scanning website... Please wait!")
    
    result = await find_payment_gateways(url)

    if "error" in result:
        await status_message.edit_text(f"❌ Error: {result['error']}")
        return

    response_text = (
        f"🟢 **URL:** {url}\n"
        f"🎉 **Status:** {result['status']}\n"
        f"🗿 **Gateway:** {', '.join(result['gateways'])}\n"
        f"🤖 **Captcha:** {result['captcha']}\n"
        f"☁️ **Cloudflare:** {result['cloudflare']}\n"
        f"🛸 **Platform:** {result['platform']}\n"
        f"🌐 **Server:** {result['server']}\n"
        f"⏳ **Time Taken:** {result['time_taken']}\n"
        f"🆔 Checked By: @{message.from_user.username}"
    )

    await status_message.edit_text(response_text, parse_mode="Markdown")

# Start bot
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
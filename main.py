import requests
import re
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Replace with your bot token
BOT_TOKEN = "8126996237:AAFBKH7e7AZaVCEkALdpOuTOK3pZbJoD3f0"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# List of known payment gateway domains (Indian & International)
PAYMENT_GATEWAYS = [
    # Indian Payment Gateways
    "razorpay.com", "payu.in", "ccavenue.com", "instamojo.com", "cashfree.com",
    "paytm.com", "billdesk.com", "atomtech.in", "timesofmoney.com", "hdfcbank.com",
    "icicibank.com", "axisbank.com", "worldline.com", "nimbbl.biz", "pinelabs.com", "paykun.com",

    # International Payment Gateways
    "paypal.com", "stripe.com", "authorize.net", "squareup.com", "2checkout.com",
    "verifone.com", "braintreepayments.com", "wepay.com", "adyen.com", "checkout.com",
    "klarna.com", "skrill.com", "alipay.com", "payoneer.com", "amazonpay.com",
    "dlocal.com", "bluesnap.com", "gocardless.com", "rapyd.net", "mollie.com",

    # Cryptocurrency Payment Gateways
    "bitpay.com", "commerce.coinbase.com", "coingate.com", "nowpayments.io",
    "crypto.com/pay"
]

# Function to clean and format URL
def clean_url(input_text):
    url = input_text.strip().replace(" ", "")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url  # Assume HTTP if missing
    return url

# Function to find payment gateways
def find_payment_gateways(url):
    try:
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        if status_code != 200:
            return {"status": status_code, "error": "❌ Failed to access website"}

        soup = BeautifulSoup(response.text, "html.parser")
        found_gateways = []

        # Check for payment gateway presence in page content
        for gateway in PAYMENT_GATEWAYS:
            if gateway in response.text:
                found_gateways.append(gateway)

        return {
            "status": status_code,
            "gateways": found_gateways if found_gateways else ["⚠️ No payment gateway detected."],
            "captcha": detect_captcha(response.text),
            "cloudflare": detect_cloudflare(response.headers),
            "platform": detect_platform(url),
            "server": response.headers.get("Server", "Unknown"),
            "auth_required": detect_auth(response.text),
            "vbv": detect_vbv(response.text)
        }

    except requests.exceptions.RequestException:
        return {"status": "Error", "error": "❌ Could not fetch website"}

# Function to detect Captcha
def detect_captcha(html):
    return "Yes ⚠️" if "captcha" in html.lower() or "recaptcha" in html.lower() else "No ❌"

# Function to detect Cloudflare protection
def detect_cloudflare(headers):
    return "True ✅" if "cf-ray" in headers else "False ❌"

# Function to detect platform (Shopify, Magento, WordPress, etc.)
def detect_platform(url):
    try:
        response = requests.get(f"https://api.wappalyzer.com/v2/lookup/?urls={url}", timeout=10)
        data = response.json()
        return data.get("applications", [{}])[0].get("name", "Unknown")
    except:
        return "Unknown"

# Function to detect authentication requirement
def detect_auth(html):
    return "Yes 🔥" if "login" in html.lower() or "signin" in html.lower() else "No ❌"

# Function to detect VBV (Verified by Visa)
def detect_vbv(html):
    return "True ✅" if "verified by visa" in html.lower() or "3dsecure" in html.lower() else "False ❌"

# Telegram command handler
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("👋 Send me a website URL, and I'll find its payment gateways!\n\nYou can use:\n- Just paste the URL\n- Use `/url <website>` or `.url <website>`")

# Telegram URL processing
@dp.message_handler(lambda message: message.text.startswith(("/url", ".url")) or "." in message.text)
async def process_url(message: types.Message):
    url = clean_url(message.text.replace("/url", "").replace(".url", "").strip())
    await message.reply("🔍 Scanning website... Please wait!")

    result = find_payment_gateways(url)

    if "error" in result:
        await message.reply(f"❌ Error: {result['error']}")
        return

    # Formatting response
    response_text = (
        f"🟢 **URL:** {url}\n"
        f"🎉 **Status:** {result['status']}\n"
        f"🗿 **Gateway:** {', '.join(result['gateways'])}\n"
        f"🤖 **Captcha:** {result['captcha']}\n"
        f"☁️ **Cloudflare:** {result['cloudflare']}\n"
        f"🛸 **Platform:** {result['platform']}\n"
        f"🌐 **Server:** {result['server']}\n"
        f"-> **Auth:** {result['auth_required']}\n"
        f"-> **Vbv:** {result['vbv']}\n"
        f"🆔 Checked By ~ wildbeastxd\n"
        f"Credits left: 24🤑"
    )

    await message.reply(response_text)

# Start bot
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
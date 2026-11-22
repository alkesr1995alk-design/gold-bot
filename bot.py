import base64
import io
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import telebot
from PIL import Image

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9208754077:AAGPyOzAgNO43J5ESMYyH6rY8YJ-mQ2tE8o")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip()

bot = telebot.TeleBot(BOT_TOKEN)

waiting_for_capital = {}

PROMPT = """
حلل صورة شارت التداول للسكالبينج السريع باستراتيجية SMC. 
أجب باختصار شديد من أرقام الشارت الظاهرة فقط:
- الاتجاه العام:
- القرار: (BUY أو SELL أو WAIT)
- نقطة الدخول (Entry):
- وقف الخسارة (SL):
- الهدف (TP):
- السبب بسطر واحد:
"""


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def start_port_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def get_available_models(base_url):
    try:
        r = requests.get(base_url + "?key=" + GEMINI_KEY, timeout=15)
        if r.status_code == 200:
            data = r.json()
            valid = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods and "flash" in name.lower():
                    valid.append(name)
            if valid:
                return valid
    except Exception:
        pass
    return ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-flash-latest"]


def ask_gemini_image(img: Image.Image) -> str:
    if not GEMINI_KEY:
        return "مفتاح GEMINI_KEY غير مضبوط في Environment على Render."

    img_rgb = img.convert("RGB")
    img_rgb.thumbnail((800, 800))
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=75)
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

    host = "generativelanguage" + "." + "googleapis" + "." + "com"
    base_url = "https://" + host + "/v1beta/models"
    models = get_available_models(base_url)

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}},
                ]
            }
        ]
    }

    last_error = ""
    for model_name in models:
        url = base_url + "/" + model_name + ":generateContent?key=" + GEMINI_KEY
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text_out = "".join(p.get("text", "") for p in parts).strip()
                    if text_out:
                        return text_out
            else:
                last_error = f"({r.status_code}) في {model_name}: {r.text[:150]}"
        except Exception as e:
            last_error = str(e)[:150]

    return f"تعذر التحليل. آخر خطأ: {last_error}"


@bot.message_handler(commands=["start"])
def send_welcome(message):
    welcome_text = (
        "أهلاً بك يا بطل في بوت تحليل الذهب (SMC)! 📊✨\n\n"
        "كيف أستطيع مساعدتك اليوم؟\n"
        "أرسل لي لقطة شاشة واضحة للشارت وسأقوم بتحليلها فوراً وإعطائك خطة الصفقة وإدارة رأس المال."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    bot.reply_to(message, "⏳ جاري قراءة الشموع وتحليل السيولة...")
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    img = Image.open(io.BytesIO(downloaded))
    result = ask_gemini_image(img)
    bot.reply_to(message, result)
    
    waiting_for_capital[message.chat.id] = True
    bot.send_message(message.chat.id, "💰 كم يبلغ رأس مالك الحالي بالدولار (اكتب الرقم فقط مثل: 50 أو 100) لأحسب لك حجم العقد الآمن؟")


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if waiting_for_capital.get(chat_id):
        try:
            capital = float(message.text.strip())
            risk = capital * 0.02
            lot = 0.01 if capital < 500 else round((capital / 500) * 0.01, 2)
            reply = (
                f"📊 خطة إدارة رأس المال لحسابك (${capital}):\n"
                f"• أقصى خسارة مسموحة للصفقة (2%): ${risk:.2f}\n"
                f"• حجم العقد الموصى به (Lot): {lot}\n\n"
                f"أرسل صورة شارت جديدة في أي وقت!"
            )
            bot.reply_to(message, reply)
            waiting_for_capital[chat_id] = False
        except ValueError:
            bot.reply_to(message, "يرجى إرسال رقم صحيح لرأس المال فقط (مثال: 100):")
    else:
        bot.reply_to(message, "أهلاً بك! كيف أساعدك؟ أرسل لي صورة للشارت لأقوم بتحليلها لك الآن.")


if __name__ == "__main__":
    threading.Thread(target=start_port_server, daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    print("Bot started...")
    bot.infinity_polling(skip_pending=True)
            

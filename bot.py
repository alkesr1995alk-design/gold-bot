import base64
import io
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import telebot
from PIL import Image

BOT_TOKEN = "9208754077:AAEgYXa84Q6C16CFTYXJa1A9phfM_A_4v-4"
GEMINI_KEY = "AQ.Ab8RN6Laiw0BnSBcQA6hXnSvfBY8gZc2qw8Yr5nrytlPM58GYQ"

bot = telebot.TeleBot(BOT_TOKEN)

PROMPT = "حلل صورة شارت التداول للسكالبينج السريع. أجب باختصار شديد من أرقام الشارت الظاهرة فقط: القرار (BUY أو SELL أو WAIT)، نقطة الدخول، وقف الخسارة (SL)، الهدف (TP)، والسبب بسطر واحد."


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


def ask_gemini_image(img: Image.Image) -> str:
    img_rgb = img.convert("RGB")
    img_rgb.thumbnail((800, 800))
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=65)
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_KEY,
    }
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

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=25)
        data = r.json()
        if r.status_code == 200:
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_out = "".join(p.get("text", "") for p in parts).strip()
                if text_out:
                    return text_out
        err_msg = data.get("error", {}).get("message", r.text)
        return f"API Error: {err_msg[:300]}"
    except Exception as e:
        return f"Request Error: {str(e)[:200]}"


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    bot.reply_to(message, "جاري تحليل الشارت...")
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    img = Image.open(io.BytesIO(downloaded))
    result = ask_gemini_image(img)
    bot.reply_to(message, result)


if __name__ == "__main__":
    threading.Thread(target=start_port_server, daemon=True).start()
    print("Bot started...")
    bot.infinity_polling(skip_pending=True)

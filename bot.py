import base64
import io
import time
import requests
import telebot
from PIL import Image

BOT_TOKEN = "9208754077:AAEgYXa84Q6C16CFTYXJa1A9phfM_A_4v-4"
GEMINI_KEY = "AQ.Ab8RN6KzQy9wHfRs3Prk-pTcXLUSS0Dq-49jGFWSio-Al9wLmA"

bot = telebot.TeleBot(BOT_TOKEN)

PROMPT = """
حلل صورة شارت التداول هذه للسكالبينج السريع. أجب باختصار شديد وبدقة أرقام الشارت الظاهرة فقط:
- القرار: (BUY أو SELL أو WAIT)
- نقطة الدخول الدقيقة:
- وقف الخسارة (SL):
- الهدف (TP):
- السبب بسطر واحد:
"""


def ask_gemini_image(img: Image.Image) -> str:
    img_rgb = img.convert("RGB")
    img_rgb.thumbnail((800, 800))
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=65)
    b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.8-flash:generateContent?key={GEMINI_KEY}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_img,
                        }
                    },
                ]
            }
        ]
    }

    for attempt in range(1, 3):
        try:
            r = requests.post(url, json=payload, timeout=25)
            data = r.json()

            if r.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text_out = "".join(p.get("text", "") for p in parts).strip()
                    if text_out:
                        return text_out
                return "No text in response: " + str(data)[:300]

            err_msg = str(data.get("error", {}).get("message", r.text))
            if "high demand" in err_msg.lower() or r.status_code in (429, 500, 503):
                time.sleep(2)
                continue

            return "API Error: " + err_msg[:300]

        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return "Network/Timeout Error: " + str(e)

    return "API Error: النموذج مشغول حالياً، جرّب بعد قليل."


@bot.message_handler(content_types=["photo"])
def analyze_chart(message):
    msg = bot.reply_to(message, "جاري التحليل...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        img = Image.open(io.BytesIO(downloaded))
        result = ask_gemini_image(img)
        bot.edit_message_text(result, chat_id=msg.chat.id, message_id=msg.message_id)
    except Exception as e:
        err = "Handler Error: " + str(e)
        bot.edit_message_text(err, chat_id=msg.chat.id, message_id=msg.message_id)


print("Bot started 24/7...", flush=True)
bot.polling(none_stop=True, timeout=20, long_polling_timeout=20)

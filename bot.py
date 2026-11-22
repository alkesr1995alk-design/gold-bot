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
    print("Bot started...")
    bot.infinity_polling(skip_pending=True)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from flask import Flask, request
from threading import Thread
import paypalrestsdk
import logging
import requests
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


paypalrestsdk.configure({
    "mode": "sandbox",  
    "client_id": "AaG0qpK3JRrD5wOIeXf1Zsl_VGiv7I78xuqadyHD0Kbac7X1UqOGaoswyUxY4lwqBFYiJD5A_pC3XYEU",
    "client_secret": "EMezdRa7bCX2Y25YsRhwsSZfojos5yqJJQpVeFuSfbbHbfAc3IRQK6QDCPHISp1AFaRq7mrutc6xY5Mt"
})

app = Flask(__name__)

BOT_TOKEN = "7694452169:AAGhKM51jaUlVk3sC4d_3CFF-znrCgB6mB8"

application = Application.builder().token(BOT_TOKEN).build()

user_chat_ids = {}

async def handle_start_or_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user_chat_ids[chat_id] = chat_id  

    text = "Привет! Пожалуйста, выберите способ оплаты. Нажмите 'Купить', чтобы начать процесс оплаты."
    keyboard = [[InlineKeyboardButton("Купить", callback_data='buy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup)


def create_payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "https://4c41-185-48-148-202.ngrok-free.app/payment/execute",
            "cancel_url": "https://4c41-185-48-148-202.ngrok-free.app/payment/cancel"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "Test File",
                    "sku": "001",
                    "price": "10.00",
                    "currency": "USD",
                    "quantity": 1}]},
            "amount": {
                "total": "10.00",
                "currency": "USD"},
            "description": "Test file download"}]})

    if payment.create():
        logger.info("Payment created successfully")
        for link in payment.links:
            if link.rel == "approval_url":
                return link.href  
    else:
        logger.error(payment.error)
        return None

# инлайн-кнопка
async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  

    if query.data == 'buy':
        payment_url = create_payment()
        if payment_url:
            await query.edit_message_text(text=f"Перейдите по ссылке для оплаты: {payment_url}")
        else:
            await query.edit_message_text(text="Ошибка при создании платежа.")

@app.route('/', methods=['GET'])
def index():
    return "Webhook is working!"

@app.route('/payment/execute', methods=['GET', 'POST'])
async def execute():
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request data: {request.data}")
    logger.info(f"Request args: {request.args}")

    if request.method == 'POST':
        data = request.json
        payment_id = data.get('paymentId')
        payer_id = data.get('PayerID')
    else:
        payment_id = request.args.get('paymentId')
        payer_id = request.args.get('PayerID')

    if not payment_id or not payer_id:
        logger.error("Payment ID or Payer ID not provided")
        return "Payment ID or Payer ID not provided", 400

    try:
        payment = paypalrestsdk.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            chat_id = next(iter(user_chat_ids.values()), None)
            if chat_id:
                pdf_url = 'https://www.jmir.org/2018/4/e129/PDF'  
                response = requests.get(pdf_url)
                if response.status_code == 200:
                    await application.bot.send_document(chat_id=chat_id, document=response.content, filename='file.pdf')
                else:
                    logger.error("Error downloading the PDF file")

                return "Payment executed successfully"
            else:
                logger.error("Chat ID not found for payment")
                return "Chat ID not found", 500
        else:
            logger.error(payment.error)
            return "Payment failed", 500
    except Exception as e:
        logger.error(f"Error during payment execution: {str(e)}")
        return "Internal Server Error", 500

def main():
    # обработчики команд и сообщений
    application.add_handler(CommandHandler("start", handle_start_or_message))
    application.add_handler(CallbackQueryHandler(button_callback))  # Обработчик для инлайн кнопки

    # запускаем сервера
    flask_thread = Thread(target=app.run, kwargs={'port': 5000, 'debug': True, 'use_reloader': False})
    flask_thread.start()

    application.run_polling()

if __name__ == '__main__':
    main()

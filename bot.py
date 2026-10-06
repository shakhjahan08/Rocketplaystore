import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. Replace with your actual tokens from @BotFather
BOT_TOKEN = "YOUR_BOT_FATHER_TOKEN"
PAYME_TOKEN = "YOUR_PAYME_PROVIDER_TOKEN"
CLICK_TOKEN = "YOUR_CLICK_PROVIDER_TOKEN"

GAMES_CATALOG = {
    "game_1": {
        "title": "Cyberpunk 2077",
        "price_uzs": 32000000,  # 320,000 UZS
        "description": "Digital License Key for Cyberpunk 2077",
        "code": "CYBER-9981-X821-PAYD"
    },
    "game_2": {
        "title": "Elden Ring",
        "price_uzs": 45000000,  # 450,000 UZS
        "description": "Digital License Key for Elden Ring",
        "code": "ELDEN-7732-K992-LIVE"
    },
    "game_3": {
        "title": "FC 26 / FIFA",
        "price_uzs": 50000000,  # 500,000 UZS
        "description": "Digital Key for FC 26",
        "code": "FC26-1102-MM88-GAME"
    }
}

async def safe_answer(query):
    try:
        await query.answer()
    except BadRequest:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for game_id, game in GAMES_CATALOG.items():
        formatted_price = f"{game['price_uzs'] // 100:,} UZS"
        button_text = f"🎮 {game['title']} - {formatted_price}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"select_{game_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🚀 *Welcome to Rocket Store!*\n\nSelect a game to buy:"

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    game_id = query.data.replace("select_", "")
    game = GAMES_CATALOG.get(game_id)

    if not game:
        await query.edit_message_text("Game not found.")
        return

    keyboard = [
        [
            InlineKeyboardButton("💳 Payme", callback_data=f"pay_payme_{game_id}"),
            InlineKeyboardButton("🔹 Click", callback_data=f"pay_click_{game_id}")
        ],
        [InlineKeyboardButton("« Back to Catalog", callback_data="back_to_catalog")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    formatted_price = f"{game['price_uzs'] // 100:,} UZS"
    text = f"🚀 *{game['title']}*\n\n📝 {game['description']}\n💰 Price: *{formatted_price}*\n\nSelect payment method:"
    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_payment_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    data = query.data
    if data == "back_to_catalog":
        await start(update, context)
        return

    # Fix: Correctly extract provider and game_id from callback_data (e.g. 'pay_payme_game_2')
    parts = data.split("_")
    provider_type = parts[1]        # 'payme' or 'click'
    game_id = f"{parts[2]}_{parts[3]}"  # 'game_2'

    game = GAMES_CATALOG.get(game_id)
    if not game:
        await query.edit_message_text("Game not found.")
        return

    provider_token = PAYME_TOKEN if provider_type == "payme" else CLICK_TOKEN
    prices = [LabeledPrice(game["title"], game["price_uzs"])]

    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=f"Buy {game['title']}",
        description=game["description"],
        payload=f"payload_{game_id}",
        provider_token=provider_token,
        currency="UZS",
        prices=prices,
        start_parameter=f"buy-{game_id}"
    )
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("payload_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Error processing checkout.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    game_id = payment.invoice_payload.replace("payload_", "")
    game = GAMES_CATALOG.get(game_id)

    if game:
        await update.message.reply_text(
            f"🎉 *Payment Successful!*\n\n"
            f"🎮 *Game:* {game['title']}\n"
            f"🔑 *Key:* {game['code']}\n\n"
            f"Thank you for shopping at Rocket Store 🚀",
            parse_mode="Markdown"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

if name == 'main':
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_game_selection, pattern="^select_"))
    app.add_handler(CallbackQueryHandler(handle_payment_choice, pattern="^(pay_|back_to_catalog)"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    app.add_error_handler(error_handler)

    print("Rocket Store Bot is running...")
    app.run_polling()
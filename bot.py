print("VERSION 3 - IMAGE COMPRESSOR")

import os
import io
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from PIL import Image

BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()

# =========================
# BASIC ROUTES (FOR TESTING)
# =========================

@app.get("/")
async def root():
    return {"status": "server running"}

@app.get("/routes")
async def show_routes():
    return [route.path for route in app.routes]

# =========================
# TELEGRAM APP
# =========================

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Store user mode
user_mode = {}

# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is working!\n\n"
        "Use /image_resizer to compress an image."
    )

async def image_resizer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_mode[user_id] = "compress"
    await update.message.reply_text("📸 Send the image you want to compress.")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("image_resizer", image_resizer_command))

# =========================
# IMAGE HANDLER
# =========================

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_mode.get(user_id) != "compress":
        return

    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(file_bytes))

        output = io.BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=40, optimize=True)
        output.seek(0)

        await update.message.reply_photo(
            photo=output,
            caption="✅ Compressed Image"
        )

        user_mode[user_id] = None

    except Exception as e:
        await update.message.reply_text("❌ Error processing image.")

telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_image))

# =========================
# STARTUP & SHUTDOWN
# =========================

@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.start()
    print("Telegram application started")

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()

# =========================
# WEBHOOK
# =========================

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

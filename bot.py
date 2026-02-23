print("VERSION 4 - TARGET SIZE COMPRESSOR")

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

@app.get("/")
async def root():
    return {"status": "server running"}

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Store user state
user_data = {}

# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is working!\n\n"
        "Use /image_resizer to compress image to specific KB size."
    )

async def image_resizer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {"step": "ask_size"}
    await update.message.reply_text("📏 Enter target size in KB (example: 200)")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("image_resizer", image_resizer))

# =========================
# TEXT HANDLER (FOR SIZE INPUT)
# =========================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id in user_data and user_data[user_id].get("step") == "ask_size":
        if not text.isdigit():
            await update.message.reply_text("❌ Please enter a valid number in KB.")
            return

        user_data[user_id]["target_kb"] = int(text)
        user_data[user_id]["step"] = "wait_image"
        await update.message.reply_text("📸 Now send the image.")
        return

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# =========================
# IMAGE HANDLER
# =========================

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data:
        return

    if user_data[user_id].get("step") != "wait_image":
        return

    target_kb = user_data[user_id]["target_kb"]
    target_bytes = target_kb * 1024

    try:
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    output = io.BytesIO()

    min_q = 10
    max_q = 95
    best_output = None

    while min_q <= max_q:
        mid_q = (min_q + max_q) // 2

        output.seek(0)
        output.truncate()

        image.save(output, format="JPEG", quality=mid_q, optimize=True)
        size = output.tell()

        if size > target_bytes:
            max_q = mid_q - 1
        else:
            best_output = output.getvalue()
            min_q = mid_q + 1

    if best_output:
        output = io.BytesIO(best_output)

    output.seek(0)

    final_kb = round(output.tell() / 1024, 2)

    await update.message.reply_photo(
        photo=output,
        caption=f"✅ Compressed Image\n📦 Final Size: {final_kb} KB\n🎯 Target: {target_kb} KB"
    )

    user_data.pop(user_id)

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

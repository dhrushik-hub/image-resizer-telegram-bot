print("VERSION 5 - IMAGE + OJAS PRESET")

import os
import io
from fastapi import FastAPI, Request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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

# =========================
# USER STATE STORAGE
# =========================
user_data = {}

# =========================
# START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot is working!\n\n"
        "Commands:\n"
        "/image_resizer → Compress by custom KB\n"
        "/ojas → OJAS Photo & Signature preset"
    )

telegram_app.add_handler(CommandHandler("start", start))

# =========================
# IMAGE RESIZER (CUSTOM KB)
# =========================
async def image_resizer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {"mode": "custom", "step": "ask_size"}
    await update.message.reply_text("📏 Enter target size in KB (example: 200)")

telegram_app.add_handler(CommandHandler("image_resizer", image_resizer))


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
# OJAS PRESET COMMAND
# =========================
async def ojas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("OJAS PHOTO & Signature", callback_data="ojas")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select preset:", reply_markup=reply_markup)

telegram_app.add_handler(CommandHandler("ojas", ojas_command))


async def preset_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ojas":
        user_id = query.from_user.id
        user_data[user_id] = {
            "mode": "ojas_photo",
            "step": "wait_photo"
        }
        await query.message.reply_text(
            "📸 Send PHOTO\n"
            "Required Size: 5cm x 3.6cm\n"
            "Max: 15 KB"
        )

telegram_app.add_handler(CallbackQueryHandler(preset_selected))

# =========================
# IMAGE HANDLER (BOTH MODES)
# =========================
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data:
        return

    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        # =========================
        # CUSTOM KB MODE
        # =========================
        if user_data[user_id]["mode"] == "custom":
            target_kb = user_data[user_id]["target_kb"]

        # =========================
        # OJAS PHOTO MODE
        # =========================
        elif user_data[user_id]["mode"] == "ojas_photo":
            image = image.resize((189, 136))  # 5cm x 3.6cm
            target_kb = 15
            user_data[user_id]["mode"] = "ojas_signature"
            await update.message.reply_text(
                "✍ Now send SIGNATURE\n"
                "Required Size: 2.5cm x 7.5cm\n"
                "Max: 15 KB"
            )

        # =========================
        # OJAS SIGNATURE MODE
        # =========================
        elif user_data[user_id]["mode"] == "ojas_signature":
            image = image.resize((283, 95))  # 7.5cm x 2.5cm
            target_kb = 15
            user_data.pop(user_id)

        else:
            return

        # =========================
# SMART COMPRESSION
# =========================
output = io.BytesIO()

# For CUSTOM mode
if user_data[user_id]["mode"] == "custom":
    min_bytes = target_kb * 1024
    max_bytes = target_kb * 1024

# For OJAS mode (11KB to 14KB range)
else:
    min_bytes = 11 * 1024
    max_bytes = 14 * 1024

min_q = 50   # start from better quality
max_q = 95
best_output = None

while min_q <= max_q:
    mid_q = (min_q + max_q) // 2

    output.seek(0)
    output.truncate()

    image.save(output, format="JPEG", quality=mid_q, optimize=True)
    size = output.tell()

    if size > max_bytes:
        max_q = mid_q - 1
    elif size < min_bytes:
        min_q = mid_q + 1
    else:
        best_output = output.getvalue()
        min_q = mid_q + 1

# If perfect range not found, use good quality fallback
if not best_output:
    output.seek(0)
    output.truncate()
    image.save(output, format="JPEG", quality=85, optimize=True)
    best_output = output.getvalue()

output = io.BytesIO(best_output)

final_bytes = len(best_output)
final_kb = round(final_bytes / 1024, 2)

output.seek(0)


        await update.message.reply_photo(
            photo=output,
            caption=f"✅ Done\n📦 Final Size: {final_kb} KB"
        )

    except Exception:
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

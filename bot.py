import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

BOT_TOKEN = os.getenv("8061079165:AAELYBVwL_HWoRWMkV2fB5jD32-_qvQDhWk")
API_KEY = os.getenv("MY_SUPER_SECRET_KEY_2026")
BACKEND_URL = "https://image-resizer-bot-nrmq.onrender.com"

user_mode = {}

# =============================
# START
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to Image Resizer Bot!\n\n"
        "Send an image → Convert to PDF\n\n"
        "Commands:\n"
        "/image_resizer\n"
        "/pdf_resizer\n"
        "/pdf_merge"
    )

# =============================
# MODE COMMANDS
# =============================
async def image_resizer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = "image_resizer"
    await update.message.reply_text("Send image to resize (default 800x800).")

async def pdf_resizer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = "pdf_resizer"
    await update.message.reply_text("Send PDF to compress.")

async def pdf_merge_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_mode[update.effective_user.id] = "pdf_merge"
    await update.message.reply_text("Send PDFs one by one. Type /done when finished.")

# =============================
# HANDLE IMAGE
# =============================
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = user_mode.get(update.effective_user.id, "image_to_pdf")

    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = "temp.jpg"
    await file.download_to_drive(file_path)

    if mode == "image_resizer":
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{BACKEND_URL}/image-resizer/",
                files={"file": f},
                headers={"x-api-key": API_KEY},
                data={"width": 800, "height": 800}
            )

    else:  # Default image to PDF
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{BACKEND_URL}/image-to-pdf/",
                files={"file": f}
            )

    if response.status_code == 200:
        output_file = "output"
        if mode == "image_resizer":
            output_file += ".jpg"
        else:
            output_file += ".pdf"

        with open(output_file, "wb") as f:
            f.write(response.content)

        await update.message.reply_document(document=open(output_file, "rb"))
    else:
        await update.message.reply_text("❌ Processing failed.")

# =============================
# HANDLE PDF
# =============================
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = user_mode.get(update.effective_user.id)

    document = update.message.document
    file = await document.get_file()
    file_path = document.file_name
    await file.download_to_drive(file_path)

    if mode == "pdf_resizer":
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{BACKEND_URL}/pdf-resizer/",
                files={"file": f},
                headers={"x-api-key": API_KEY},
                data={"target_size": 1, "size_unit": "MB"}
            )

        if response.status_code == 200:
            with open("compressed.pdf", "wb") as f:
                f.write(response.content)

            await update.message.reply_document(document=open("compressed.pdf", "rb"))
        else:
            await update.message.reply_text("❌ PDF compression failed.")

# =============================
# RUN BOT
# =============================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("image_resizer", image_resizer_mode))
app.add_handler(CommandHandler("pdf_resizer", pdf_resizer_mode))
app.add_handler(CommandHandler("pdf_merge", pdf_merge_mode))

app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

app.run_polling()

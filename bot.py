import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

user_mode = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to Image Resizer Bot!\n\n"
        "Commands:\n"
        "/image_resizer\n"
        "/pdf_resizer\n"
        "/pdf_merge\n\n"
        "Or just send an image."
    )

async def image_resizer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send image to resize.")

async def pdf_resizer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Send PDF to compress.")

async def pdf_merge_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📑 Send multiple PDFs to merge.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Image received ✅")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("PDF received ✅")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("image_resizer", image_resizer_mode))
telegram_app.add_handler(CommandHandler("pdf_resizer", pdf_resizer_mode))
telegram_app.add_handler(CommandHandler("pdf_merge", pdf_merge_mode))

telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
telegram_app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

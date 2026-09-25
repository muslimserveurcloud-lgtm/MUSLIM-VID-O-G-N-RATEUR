"""
Bot Telegram : envoie du texte (et éventuellement une image en légende)
et reçois en retour une courte vidéo générée automatiquement (max 30s),
sans API payante.

Lancement : python bot.py
Configuration : voir .env.example
"""

import logging
import os
import tempfile

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from video_generator import MAX_DURATION, generate_video

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Salut ! Envoie-moi un texte et je t'en fais une courte vidéo "
        f"(jusqu'à {MAX_DURATION}s).\n\n"
        "Tu peux aussi m'envoyer une image avec une légende : "
        "j'utiliserai ton image comme fond et ta légende comme texte."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Envoie-moi un texte non vide 🙂")
        return
    await _generate_and_send(update, text, background_image_path=None)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = (update.message.caption or "").strip()
    photo = update.message.photo[-1]  # plus haute résolution disponible
    file = await context.bot.get_file(photo.file_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        image_path = os.path.join(tmp_dir, "background.jpg")
        await file.download_to_drive(image_path)
        await _generate_and_send(update, caption, background_image_path=image_path)


async def _generate_and_send(
    update: Update, text: str, background_image_path: str
) -> None:
    status_msg = await update.message.reply_text("Génération de la vidéo… ⏳")
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "video.mp4")
            generate_video(text, output_path, background_image_path=background_image_path)
            with open(output_path, "rb") as video_file:
                await update.message.reply_video(
                    video_file, caption=(text[:1024] if text else None)
                )
    except Exception:
        logger.exception("Échec de génération de vidéo")
        await update.message.reply_text(
            "Désolé, la génération a échoué. Réessaie avec un texte plus court."
        )
    finally:
        await status_msg.delete()


def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "Variable d'environnement TELEGRAM_BOT_TOKEN manquante. "
            "Copie .env.example en .env et renseigne ton token (obtenu via @BotFather)."
        )

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot démarré (polling)…")
    application.run_polling()


if __name__ == "__main__":
    main()

"""
MUSLIM VIDEO GENERATOR - Bot Telegram

Bot Telegram qui génère automatiquement de courtes vidéos à partir :
- d'un texte ;
- d'une image avec une légende.

Compatible avec Render Web Service :
- le bot Telegram fonctionne en polling ;
- un serveur HTTP /health écoute sur le PORT fourni par Render.
"""

import logging
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Petit serveur HTTP utilisé par Render pour vérifier le service."""

    def do_GET(self):
        if self.path in ("/", "/health", "/health/"):
            body = b'{"ok":true,"service":"MUSLIM VIDEO GENERATOR"}'

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = b'{"ok":false,"error":"Not Found"}'

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Évite de remplir inutilement les logs Render.
        return


def start_health_server():
    """Démarre le serveur HTTP dans un thread séparé."""
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)

    logger.info("Serveur HTTP démarré sur le port %s", PORT)

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    return server


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    await update.message.reply_text(
        "🎬 MUSLIM VIDEO GENERATOR\n\n"
        "Envoie-moi un texte et je vais créer une courte vidéo "
        f"(jusqu'à {MAX_DURATION} secondes).\n\n"
        "Tu peux aussi envoyer une image avec une légende : "
        "l'image servira de fond et la légende sera affichée dans la vidéo."
    )


async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    text = (update.message.text or "").strip()

    if not text:
        await update.message.reply_text(
            "Envoie-moi un texte non vide 🙂"
        )
        return

    await _generate_and_send(
        update,
        text,
        background_image_path=None,
    )


async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    if not update.message.photo:
        return

    caption = (update.message.caption or "").strip()

    photo = update.message.photo[-1]
    telegram_file = await context.bot.get_file(photo.file_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        image_path = os.path.join(
            tmp_dir,
            "background.jpg",
        )

        await telegram_file.download_to_drive(image_path)

        await _generate_and_send(
            update,
            caption,
            background_image_path=image_path,
        )


async def _generate_and_send(
    update: Update,
    text: str,
    background_image_path: str = None,
) -> None:
    if not update.message:
        return

    status_msg = None

    try:
        status_msg = await update.message.reply_text(
            "🎬 Génération de la vidéo… ⏳"
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(
                tmp_dir,
                "video.mp4",
            )

            generate_video(
                text,
                output_path,
                background_image_path=background_image_path,
            )

            with open(output_path, "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=text[:1024] if text else None,
                )

    except Exception:
        logger.exception(
            "Échec de génération ou d'envoi de la vidéo"
        )

        try:
            await update.message.reply_text(
                "❌ Désolé, la génération de la vidéo a échoué.\n\n"
                "Réessaie avec un texte plus court ou une autre image."
            )
        except Exception:
            logger.exception(
                "Impossible d'envoyer le message d'erreur"
            )

    finally:
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass


def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN est manquant. "
            "Ajoute cette variable dans les Environment Variables de Render."
        )

    # Serveur HTTP nécessaire pour le Render Web Service.
    start_health_server()

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    logger.info(
        "MUSLIM VIDEO GENERATOR démarré."
    )

    logger.info(
        "Telegram polling actif."
    )

    logger.info(
        "Health check disponible sur /health."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()

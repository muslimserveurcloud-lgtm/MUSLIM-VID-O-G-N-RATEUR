"""
Génération de courtes vidéos (max 30s) à partir de texte, avec un fond
soit par défaut (dégradé), soit fourni par l'utilisateur (image).
"""

import os
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import CompositeVideoClip, ImageClip

# Résolution vidéo (format portrait, adapté à Telegram / réseaux sociaux)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

MAX_DURATION = 30  # secondes — plafond imposé
MIN_DURATION = 4
WORDS_PER_SECOND = 2.3  # vitesse de lecture approximative, pour calculer la durée

# Chemins de police à essayer dans l'ordre (Linux/Render puis Termux/Android).
# Ajoute ici le chemin d'une police .ttf que tu embarques toi-même si tu veux
# un rendu plus soigné.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    os.path.join(os.path.dirname(__file__), "assets", "font.ttf"),
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # Filet de sécurité : police bitmap intégrée à Pillow (moins jolie mais
    # toujours disponible, aucune dépendance système requise).
    return ImageFont.load_default()


def _gradient_background(
    color_top=(20, 20, 40), color_bottom=(60, 20, 90)
) -> Image.Image:
    """Crée un fond en dégradé vertical, utilisé si aucune image n'est fournie."""
    base = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), color_top)
    draw = ImageDraw.Draw(base)
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))
    return base


def _fit_background(image_path: str) -> Image.Image:
    """Redimensionne/recadre l'image fournie par l'utilisateur pour remplir le cadre."""
    img = Image.open(image_path).convert("RGB")
    src_ratio = img.width / img.height
    dst_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    if src_ratio > dst_ratio:
        new_height = VIDEO_HEIGHT
        new_width = int(new_height * src_ratio)
    else:
        new_width = VIDEO_WIDTH
        new_height = int(new_width / src_ratio)
    img = img.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - VIDEO_WIDTH) // 2
    top = (new_height - VIDEO_HEIGHT) // 2
    return img.crop((left, top, left + VIDEO_WIDTH, top + VIDEO_HEIGHT))


def _draw_text_overlay(text: str) -> Image.Image:
    """Dessine le texte centré (avec retour à la ligne auto) sur un calque transparent."""
    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    max_text_width = int(VIDEO_WIDTH * 0.85)
    font_size = 80
    font = _load_font(font_size)
    wrapped_lines = [text]

    # Réduit la taille de police jusqu'à ce que le texte tienne dans le cadre.
    while font_size > 24:
        font = _load_font(font_size)
        chars_per_line = max(6, int(max_text_width / (font_size * 0.55)))
        wrapped_lines = textwrap.wrap(text, width=chars_per_line) or [""]
        line_boxes = [draw.textbbox((0, 0), line, font=font) for line in wrapped_lines]
        total_height = sum(b[3] - b[1] for b in line_boxes) + (len(wrapped_lines) - 1) * 14
        max_width = max((b[2] - b[0] for b in line_boxes), default=0)
        if total_height < VIDEO_HEIGHT * 0.6 and max_width < max_text_width:
            break
        font_size -= 4

    line_boxes = [draw.textbbox((0, 0), line, font=font) for line in wrapped_lines]
    line_heights = [b[3] - b[1] for b in line_boxes]
    total_height = sum(line_heights) + (len(wrapped_lines) - 1) * 14
    max_line_width = max((b[2] - b[0] for b in line_boxes), default=0)

    y = (VIDEO_HEIGHT - total_height) // 2
    padding = 40
    draw.rounded_rectangle(
        [
            (VIDEO_WIDTH - max_line_width) // 2 - padding,
            y - padding,
            (VIDEO_WIDTH + max_line_width) // 2 + padding,
            y + total_height + padding,
        ],
        radius=30,
        fill=(0, 0, 0, 140),
    )

    for line, box, line_height in zip(wrapped_lines, line_boxes, line_heights):
        line_width = box[2] - box[0]
        x = (VIDEO_WIDTH - line_width) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height + 14

    return overlay


def _estimate_duration(text: str) -> float:
    word_count = max(1, len(text.split()))
    duration = word_count / WORDS_PER_SECOND
    return max(MIN_DURATION, min(MAX_DURATION, duration))


def generate_video(
    text: str,
    output_path: str,
    background_image_path: str = None,
    duration: float = None,
) -> str:
    """
    Génère un MP4 (max MAX_DURATION secondes) avec `text` affiché sur un fond :
    - l'image fournie par l'utilisateur (`background_image_path`) si présente,
    - sinon un dégradé par défaut.
    """
    duration = duration or _estimate_duration(text or "")
    duration = max(MIN_DURATION, min(MAX_DURATION, duration))

    background = (
        _fit_background(background_image_path)
        if background_image_path
        else _gradient_background()
    )

    bg_clip = ImageClip(np.array(background)).set_duration(duration)
    # Léger zoom continu (effet "Ken Burns") pour dynamiser un fond statique.
    bg_clip = bg_clip.resize(lambda t: 1 + 0.04 * (t / duration))
    bg_clip = bg_clip.set_position(("center", "center"))

    clips = [bg_clip]
    if text and text.strip():
        overlay = _draw_text_overlay(text.strip())
        text_clip = ImageClip(np.array(overlay)).set_duration(duration)
        clips.append(text_clip)

    final = CompositeVideoClip(clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_duration(duration)
    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio=False,
        preset="ultrafast",
        threads=2,
        logger=None,
    )
    final.close()
    bg_clip.close()
    return output_path

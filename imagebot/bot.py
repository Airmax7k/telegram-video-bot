"""Bot Telegram de génération d'images par IA."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from imagebot.generator import SIZES, STYLES, GenerationError, ImageProvider, build_provider, parse_prompt

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("imagebot")

HELP_TEXT = (
    "🎨 *Bot de génération d'images IA*\n\n"
    "Envoie simplement une description et je crée l'image !\n\n"
    "*Commandes*\n"
    "/imagine `<description>` — générer une image\n"
    "/style — choisir un style par défaut\n"
    "/taille — choisir le format (carré, portrait, paysage)\n"
    "/help — afficher cette aide\n\n"
    "*Options dans le message*\n"
    "`--style anime` · `--taille paysage` · `--seed 42`\n\n"
    "Exemple : `un dragon au-dessus de Paris --style art --taille paysage`"
)


def _allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    allowed: set[int] = context.bot_data["allowed_users"]
    return not allowed or (update.effective_user is not None and update.effective_user.id in allowed)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(HELP_TEXT)


async def choose_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [InlineKeyboardButton(s, callback_data=f"style:{s}") for s in STYLES]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton("Aucun", callback_data="style:none")])
    await update.message.reply_text("Choisis un style par défaut :", reply_markup=InlineKeyboardMarkup(rows))


async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    row = [InlineKeyboardButton(s, callback_data=f"taille:{s}") for s in SIZES]
    await update.message.reply_text("Choisis un format :", reply_markup=InlineKeyboardMarkup([row]))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    kind, value = query.data.split(":", 1)
    if kind == "style":
        context.user_data["style"] = None if value == "none" else value
        await query.edit_message_text(f"✅ Style par défaut : {value if value != 'none' else 'aucun'}")
    elif kind == "taille":
        context.user_data["taille"] = value
        await query.edit_message_text(f"✅ Format : {value}")
    elif kind == "regen":
        prompt = context.user_data.get("last_prompt")
        if not prompt:
            await query.message.reply_text("Je n'ai plus la dernière description, renvoie-la moi.")
            return
        await _generate(update, context, prompt)


async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _generate(update, context, " ".join(context.args))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _generate(update, context, update.message.text)


async def _generate(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    message = update.effective_message
    if not _allowed(update, context):
        await message.reply_text("⛔ Tu n'es pas autorisé à utiliser ce bot.")
        return
    try:
        req = parse_prompt(text, context.user_data.get("style"), context.user_data.get("taille", "carre"))
    except GenerationError as e:
        await message.reply_text(f"⚠️ {e}")
        return

    context.user_data["last_prompt"] = text
    provider: ImageProvider = context.bot_data["provider"]
    status = await message.reply_text("🎨 Génération en cours…")
    await context.bot.send_chat_action(message.chat_id, ChatAction.UPLOAD_PHOTO)
    try:
        image = await provider.generate(req)
    except GenerationError as e:
        await status.edit_text(f"❌ {e}")
        return
    except Exception:
        log.exception("Échec de génération pour %r", req.prompt)
        await status.edit_text("❌ Une erreur inattendue est survenue, réessaie plus tard.")
        return

    caption = req.prompt[:900]
    if req.style:
        caption += f"\n🎭 {req.style}"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Nouvelle variante", callback_data="regen:1")]])
    await message.reply_photo(photo=image, caption=caption, reply_markup=keyboard)
    await status.delete()


def main() -> None:
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN manquant (voir .env.example)")

    provider = build_provider(os.environ.get("IMAGE_PROVIDER", "pollinations"), dict(os.environ))
    allowed = {int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x}

    app = Application.builder().token(token).concurrent_updates(True).build()
    app.bot_data.update(provider=provider, allowed_users=allowed)
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("imagine", imagine))
    app.add_handler(CommandHandler("style", choose_style))
    app.add_handler(CommandHandler("taille", choose_size))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Bot démarré avec le moteur %s", provider.name)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from config import TELEGRAM_TOKEN, FAL_KEY

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fal.ai image-to-image endpoint (image + prompt)
FAL_IMAGE_TO_IMAGE_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    welcome_message = (
        "🎨 *Welcome to the AI Image Generator Bot!*\n\n"
        "I generate images from *your image + a text prompt*.\n\n"
        "*How to use:*\n"
        "1. Send me an *image* (or multiple)\n"
        "2. Then send me a *text prompt* describing what you want\n"
        "3. I'll send you the AI-generated result!\n\n"
        "Send an image to get started. 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    help_text = (
        "🤖 *AI Image Generator Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/cancel - Cancel and clear your pending image\n\n"
        "*Flow:*\n"
        "1. Send an *image* first (I'll wait)\n"
        "2. Then send a *text prompt* (e.g. \"Make it look like a painting\")\n"
        "3. You get the generated image!\n\n"
        "Text-only messages are ignored until you've sent an image."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear pending image and confirm."""
    if context.user_data.pop("image_url", None):
        await update.message.reply_text("Cancelled. Your image was cleared. Send a new image when ready.")
    else:
        await update.message.reply_text("Nothing to cancel. Send an image first, then a text prompt.")


async def collect_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store the user's image and wait for a text prompt."""
    # Use the largest photo (last in the list)
    photo = update.message.photo[-1]
    user = update.effective_user

    try:
        file = await context.bot.get_file(photo.file_id)
        # file_path can be full URL (PTB 21+) or relative path
        path = file.file_path
        if path.startswith("http://") or path.startswith("https://"):
            image_url = path
        else:
            image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{path}"
        context.user_data["image_url"] = image_url
        logger.info(f"User {user.id} sent image, waiting for prompt.")
        await update.message.reply_text(
            "✅ Image received. Now send me a **text prompt** to generate an image (e.g. what to change or how it should look).",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error getting file: {e}")
        await update.message.reply_text("❌ I couldn't use that image. Please try sending it again.")


async def handle_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run generation only if we have a stored image; otherwise ignore."""
    image_url = context.user_data.get("image_url")
    if not image_url:
        # No image stored: ignore (do not reply)
        return

    prompt = update.message.text
    user = update.effective_user

    # Clear stored image so the next message is ignored until they send a new image
    del context.user_data["image_url"]

    logger.info(f"User {user.id} generating with prompt: {prompt[:50]}...")

    status_message = await update.message.reply_text(
        "🎨 Generating your image... This may take a moment."
    )

    try:
        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "image_url": image_url,
            "prompt": prompt,
            "num_images": 1,
            "enable_safety_checker": True,
            "output_format": "jpeg"
        }

        response = requests.post(
            FAL_IMAGE_TO_IMAGE_URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        logger.info(f"Fal response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Fal.ai error: {response.status_code} - {response.text}")
            await status_message.edit_text(
                "❌ Something went wrong generating your image. Please try again (send an image, then a prompt)."
            )
            return

        result = response.json()

        if result and "images" in result and len(result["images"]) > 0:
            img = result["images"][0]
            image_url_out = img.get("url")
            if image_url_out:
                img_response = requests.get(image_url_out, timeout=60)
                if img_response.status_code == 200:
                    await status_message.delete()
                    await update.message.reply_photo(
                        photo=img_response.content,
                        caption=f"🎨 *Generated*\n\n📝 Prompt: _{prompt}_",
                        parse_mode="Markdown"
                    )
                    logger.info(f"Sent image to user {user.id}")
                else:
                    await status_message.edit_text(
                        "❌ Failed to download the result. Try again."
                    )
            else:
                await status_message.edit_text(
                    "❌ No image in response. Try again."
                )
        else:
            await status_message.edit_text(
                "❌ No image was generated. Try a different prompt or image."
            )

    except requests.exceptions.Timeout:
        await status_message.edit_text(
            "⏰ Request timed out. Try again (send an image, then a prompt)."
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        await status_message.edit_text(
            "❌ Network error. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_message.edit_text(
            "❌ Something went wrong. Please try again."
        )


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.PHOTO, collect_image))
    # Only triggers when user sends text; we ignore if no stored image in handle_prompt
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt)
    )

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

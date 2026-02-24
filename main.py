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

# Fal.ai API endpoints
FAL_SUBMIT_URL = "https://fal.run/fal-ai/flux/schnell"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    welcome_message = (
        "🎨 *Welcome to the AI Image Generator Bot!*\n\n"
        "I can generate images from your text descriptions using AI.\n\n"
        "*How to use:*\n"
        "Simply send me a text prompt describing the image you want, "
        "and I'll generate it for you!\n\n"
        "*Example prompts:*\n"
        "• A sunset over mountains with purple sky\n"
        "• A cute robot playing guitar\n"
        "• A futuristic city at night\n\n"
        "Send your prompt to get started! 🚀"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    help_text = (
        "🤖 *AI Image Generator Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n\n"
        "*How to generate images:*\n"
        "1. Send a text message describing the image you want\n"
        "2. Wait for the AI to generate your image\n"
        "3. Receive your generated image!\n\n"
        "*Tips for better results:*\n"
        "• Be specific and descriptive\n"
        "• Include style preferences (realistic, cartoon, etc.)\n"
        "• Mention colors, lighting, and mood\n"
        "• Add details about composition"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate an image from the user's text prompt."""
    prompt = update.message.text
    user = update.effective_user
    
    logger.info(f"User {user.id} ({user.username}) requested image: {prompt[:50]}...")
    
    # Send a "generating" message
    status_message = await update.message.reply_text(
        "🎨 Generating your image... This may take a moment."
    )
    
    try:
        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "image_size": "landscape_4_3",
            "num_images": 1,
            "enable_safety_checker": True,
            "output_format": "jpeg"
        }
        
        # Send request to Fal.ai (synchronous endpoint)
        logger.info("Submitting request to Fal.ai...")
        response = requests.post(
            FAL_SUBMIT_URL,
            headers=headers,
            json=payload,
            timeout=120  # Longer timeout for image generation
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code != 200:
            logger.error(f"Fal.ai error: {response.status_code} - {response.text}")
            await status_message.edit_text(
                "❌ Sorry, there was an error generating your image. Please try again later."
            )
            return
        
        result = response.json()
        
        # Process the result
        logger.info(f"Result keys: {result.keys() if result else 'None'}")
        
        if result and "images" in result and len(result["images"]) > 0:
            image_url = result["images"][0].get("url")
            logger.info(f"Image URL: {image_url}")
            
            if image_url:
                # Download the image
                image_response = requests.get(image_url, timeout=60)
                
                if image_response.status_code == 200:
                    # Delete the status message
                    await status_message.delete()
                    
                    # Send the image to the user
                    await update.message.reply_photo(
                        photo=image_response.content,
                        caption=f"🎨 *Generated Image*\n\n📝 Prompt: _{prompt}_",
                        parse_mode="Markdown"
                    )
                    logger.info(f"Successfully sent image to user {user.id}")
                else:
                    logger.error(f"Failed to download image: {image_response.status_code}")
                    await status_message.edit_text(
                        "❌ Failed to download the generated image. Please try again."
                    )
            else:
                logger.error("No URL in image data")
                await status_message.edit_text(
                    "❌ No image URL in response. Please try again."
                )
        else:
            logger.error(f"No images in result: {result}")
            await status_message.edit_text(
                "❌ No image was generated. Please try a different prompt."
            )
            
    except requests.exceptions.Timeout:
        await status_message.edit_text(
            "⏰ The request timed out. Please try again with a simpler prompt."
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        await status_message.edit_text(
            "❌ Network error occurred. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_message.edit_text(
            "❌ An unexpected error occurred. Please try again."
        )


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register message handler for text prompts (excluding commands)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)
    )
    
    # Log startup
    logger.info("Bot is starting...")
    
    # Run the bot until Ctrl+C is pressed
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import asyncio

# Dictionary to store images by media_group_id temporarily
media_groups = {}

async def start_photo_step(update, context):
    message = update.message
    photo_file = await message.photo[-1].get_file()
    
    # If it's part of a group, we wait a split second to collect others
    if message.media_group_id:
        if message.media_group_id not in media_groups:
            media_groups[message.media_group_id] = []
        
        media_groups[message.media_group_id].append(photo_file.file_path)
        
        # Small delay to ensure all messages in the group arrive
        await asyncio.sleep(0.5) 
        
        # Only the first message in the group will proceed to reply
        if len(media_groups[message.media_group_id]) > 0:
            context.user_data['temp_images'] = media_groups[message.media_group_id]
            # Clean up global dict
            del media_groups[message.media_group_id]
    else:
        # Single photo
        context.user_data['temp_images'] = [photo_file.file_path]

    await update.message.reply_text("Got the image(s)! Now, what should I do with them? (Send your prompt)")
    return GETTING_PROMPT
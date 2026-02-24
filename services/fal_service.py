import requests
from config import FAL_KEY

FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

def generate_image(prompt, image_urls):
    payload = {
        "prompt": prompt,
        "image_urls": image_urls,
        "enable_safety_checker": False
    }
    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(FAL_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
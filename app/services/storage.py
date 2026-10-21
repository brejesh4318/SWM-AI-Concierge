import os

import httpx
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "complaint-photos")

# SUPABASE_URL may carry a /rest/v1/ suffix; storage needs the bare project URL.
SUPABASE_PROJECT_URL = (
    (os.getenv("SUPABASE_URL") or "").split("/rest/v1")[0].rstrip("/")
)


async def save_whatsapp_photo(media_id: str, user_id: str) -> str:
    """Download a WhatsApp image and store it in Supabase Storage.

    Args:
        media_id: The WhatsApp media ID of the uploaded image.
        user_id: The user's phone number, used as the folder name.

    Returns:
        The object path inside the bucket, e.g. '918098059300/<media_id>.jpeg'.

    Raises:
        httpx.HTTPStatusError: If WhatsApp or Supabase returns an error.
    """
    whatsapp_headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        meta = await client.get(
            f"https://graph.facebook.com/v26.0/{media_id}",
            headers=whatsapp_headers,
        )
        meta.raise_for_status()
        info = meta.json()
        mime_type = info.get("mime_type", "image/jpeg")

        image = await client.get(info["url"], headers=whatsapp_headers)
        image.raise_for_status()

        path = f"{user_id}/{media_id}.{mime_type.split('/')[-1]}"

        upload = await client.post(
            f"{SUPABASE_PROJECT_URL}/storage/v1/object/{BUCKET}/{path}",
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY,
                "Content-Type": mime_type,
                "x-upsert": "true",
            },
            content=image.content,
        )
        upload.raise_for_status()

    return path

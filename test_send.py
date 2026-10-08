import asyncio

from app.services.whatsapp_service import send_text_message


async def main():
    """Send a test WhatsApp message and print the API response.

    Raises:
        httpx.HTTPError: If the request to the WhatsApp API fails.
    """
    response = await send_text_message(
        recipient_phone="918098059300",
        message="Hello from my WhatsApp chatbot! 👋"
    )

    print(response)


asyncio.run(main())
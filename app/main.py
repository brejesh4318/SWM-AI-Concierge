from fastapi import FastAPI
from app.api.webhook import router as webhook_router

app = FastAPI()
app.include_router(webhook_router)






@app.get("/")
async def root():
    """Report that the service is up.

    Returns:
        A dictionary with a 'message' key containing a status string.
    """
    return {
        "message": "WhatsApp Bot is Running"
    }
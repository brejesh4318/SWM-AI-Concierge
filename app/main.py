import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.admin import router as admin_router
from app.api.webhook import router as webhook_router
from app.core.config import get_settings
from app.core.logging import request_id_var, setup_logging, user_var

settings = get_settings()

setup_logging(settings.LOG_LEVEL, settings.LOG_JSON)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Log when the service starts and stops."""

    logger.info("WhatsApp bot started (log level %s)", settings.LOG_LEVEL)
    yield
    logger.info("WhatsApp bot stopped")


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(admin_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Give each request an id and log how it went.

    Args:
        request: The incoming request.
        call_next: Passes the request on to the route handler.

    Returns:
        The route's response, with an X-Request-ID header added.
    """

    request_id = uuid.uuid4().hex[:8]
    request_id_var.set(request_id)
    user_var.set("-")

    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "%s %s crashed", request.method, request.url.path
        )
        raise

    logger.info(
        "%s %s -> %s in %.0f ms",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/")
async def root():
    """Report that the service is up.

    Returns:
        A dictionary with a 'message' key containing a status string.
    """
    return {
        "message": "WhatsApp Bot is Running"
    }

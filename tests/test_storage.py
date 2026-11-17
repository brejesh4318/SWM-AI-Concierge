import httpx
import pytest

from app.services import storage


def install_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(
        storage.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw)
    )


async def test_save_whatsapp_photo_uploads(monkeypatch):
    monkeypatch.setattr(storage, "SUPABASE_PROJECT_URL", "https://sb.test")
    monkeypatch.setattr(storage, "BUCKET", "bkt")
    seen = {}

    def handler(request):
        url = str(request.url)
        if url.endswith("/media1"):
            return httpx.Response(
                200, json={"url": "https://cdn.test/img", "mime_type": "image/png"}
            )
        if url == "https://cdn.test/img":
            return httpx.Response(200, content=b"PNGDATA")
        seen["url"] = url
        seen["body"] = request.content
        seen["ctype"] = request.headers["content-type"]
        return httpx.Response(200, json={})

    install_transport(monkeypatch, handler)
    path = await storage.save_whatsapp_photo("media1", "9190")
    assert path == "9190/media1.png"
    assert seen["url"] == "https://sb.test/storage/v1/object/bkt/9190/media1.png"
    assert seen["body"] == b"PNGDATA" and seen["ctype"] == "image/png"


async def test_save_whatsapp_photo_default_mime_and_error(monkeypatch):
    def handler(request):
        url = str(request.url)
        if url.endswith("/m2"):
            return httpx.Response(200, json={"url": "https://cdn.test/i"})
        if url == "https://cdn.test/i":
            return httpx.Response(200, content=b"x")
        return httpx.Response(403)

    install_transport(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError):
        await storage.save_whatsapp_photo("m2", "u")

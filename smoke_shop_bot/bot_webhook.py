# -*- coding: utf-8 -*-
"""
تشغيل بنمط Webhook — لنشر البوت على Render (أو أي استضافة "Web Service" مشابهة تحتاج
سيرفر HTTP، بدل Polling العادي). شوف README.md قسم "النشر على Render" لخطوات الإعداد كاملة.

أمر التشغيل على Render: python3 bot_webhook.py
"""
import asyncio
import logging
import os

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
from telegram import Update

import app_factory
import broadcast
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main() -> None:
    render_url, broadcast_secret = config.validate_render_webhook_settings()
    token = config.validate_token()

    application = app_factory.build_application(with_updater=False)

    webhook_path = f"/webhook/{token}"
    webhook_url = f"{render_url}{webhook_path}"

    await application.bot.set_webhook(url=webhook_url, allowed_updates=["message", "callback_query"])
    logger.info("تم تسجيل الـ Webhook: %s", webhook_url)

    async def telegram_webhook(request: Request) -> Response:
        data = await request.json()
        update = Update.de_json(data=data, bot=application.bot)
        await application.update_queue.put(update)
        return Response()

    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("البوت شغّال ✅")

    async def trigger_broadcast(request: Request) -> JSONResponse:
        secret = request.path_params.get("secret", "")
        if secret != broadcast_secret:
            return JSONResponse({"error": "forbidden"}, status_code=403)
        sent, blocked = await broadcast.send_daily_broadcast(application.bot)
        return JSONResponse({"sent": sent, "blocked": blocked})

    starlette_app = Starlette(
        routes=[
            Route(webhook_path, telegram_webhook, methods=["POST"]),
            Route("/", health, methods=["GET"]),
            Route("/broadcast/{secret}", trigger_broadcast, methods=["GET", "POST"]),
        ]
    )

    port = int(os.environ.get("PORT", "10000"))
    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            host="0.0.0.0",
            port=port,
            use_colors=False,
        )
    )

    async with application:
        await application.start()
        logger.info("السيرفر شغال على المنفذ %d (Webhook mode)...", port)
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())

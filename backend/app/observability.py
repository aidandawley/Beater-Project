import logging
from typing import Awaitable, Callable

import httpx
import sentry_sdk
from fastapi import Request
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.responses import Response

from .config import settings

logger = logging.getLogger(__name__)

SENSITIVE_EVENT_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "token",
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "session",
}


def _strip_sensitive_values(event: dict, hint: dict) -> dict | None:
    request = event.get("request")
    if not isinstance(request, dict):
        return event

    headers = request.get("headers")
    if isinstance(headers, dict):
        request["headers"] = {
            key: value
            for key, value in headers.items()
            if key.lower() not in SENSITIVE_EVENT_KEYS
        }

    cookies = request.get("cookies")
    if cookies:
        request["cookies"] = "[Filtered]"

    return event


def init_sentry() -> None:
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.app_env,
        release=settings.sentry_release or None,
        send_default_pii=settings.sentry_send_default_pii,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        before_send=_strip_sensitive_values,
        integrations=[
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={*range(500, 600)},
            ),
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={*range(500, 600)},
            ),
        ],
    )


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path


def _event_payload(request: Request, status_code: int) -> dict:
    return {
        "event_type": "bogus_backend_request",
        "app": "beater-todo-lab",
        "environment": settings.sentry_environment or settings.app_env,
        "method": request.method,
        "path": request.url.path,
        "route": _route_path(request),
        "status_code": status_code,
        "query_keys": sorted(request.query_params.keys()),
    }


def capture_bogus_request_event(payload: dict) -> None:
    if not settings.bogus_request_sentry_enabled:
        return

    sentry_sdk.capture_event(
        {
            "level": "warning",
            "message": "Bogus backend request observed",
            "tags": {
                "event_type": payload["event_type"],
                "http.method": payload["method"],
                "http.status_code": str(payload["status_code"]),
                "route": payload["route"],
            },
            "extra": payload,
            "fingerprint": [
                "bogus-backend-request",
                payload["method"],
                payload["route"],
                str(payload["status_code"]),
            ],
        }
    )


async def send_bogus_request_webhook(payload: dict) -> None:
    if not settings.bogus_request_webhook_url:
        return

    headers = {"Content-Type": "application/json"}
    if settings.bogus_request_webhook_token:
        headers["Authorization"] = f"Bearer {settings.bogus_request_webhook_token}"

    try:
        async with httpx.AsyncClient(timeout=settings.bogus_request_webhook_timeout_seconds) as client:
            await client.post(settings.bogus_request_webhook_url, json=payload, headers=headers)
    except httpx.HTTPError:
        logger.exception("Failed to send bogus request webhook")


async def observe_backend_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)

    if response.status_code >= settings.bogus_request_min_status_code:
        payload = _event_payload(request, response.status_code)
        capture_bogus_request_event(payload)
        await send_bogus_request_webhook(payload)

    return response

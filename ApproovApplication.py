#!/usr/bin/env python3
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Awaitable, Callable, Iterable, Optional, cast

import jwt
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional helper dependency

    def load_dotenv() -> bool:
        return False


APPROOV_HEADER = "Approov-Token"
AUTH_HEADER = "Authorization"
SESSION_ID_HEADER = "SessionId"
PLACEHOLDER_SECRET = "approov_base64url_secret_here"
APPROOV_LOGGER_NAME = "approov"
APPROOV_SECRET_ENV = "APPROOV_BASE64URL_SECRET"
HTTP_PORT_ENV = "HTTP_PORT"
APPROOV_ENABLED_KEY = "approov_enabled"
TOKEN_BINDING_ENABLED_KEY = "token_binding_enabled"
APPROOV_TOKEN_HEADER_KEY = "approov_token_header"
APPROOV_SECRET_KEY = "approov_secret"
DEFAULT_HTTP_PORT = 8080
_MISSING = object()


class ApproovUnauthorized(Exception):
    def __init__(self, error: str) -> None:
        super().__init__(error)
        self.error = error


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _has_text(value: Optional[str]) -> bool:
    return value is not None and value.strip() != ""


def _approov_logger() -> logging.Logger:
    return logging.getLogger(APPROOV_LOGGER_NAME)


def _decode_base64url(secret: str) -> bytes:
    padding = "=" * (-len(secret) % 4)
    return base64.urlsafe_b64decode(secret + padding)


def _normalize_base64url(value: str) -> str:
    return value.strip().replace("+", "-").replace("/", "_").rstrip("=")


def _state_value(app: FastAPI, key: str, default: Any = _MISSING) -> Any:
    value = getattr(app.state, key, _MISSING)
    if value is not _MISSING:
        return value
    if default is not _MISSING:
        return default
    raise RuntimeError(f"Approov state is missing required value: {key}")


def load_approov_secret() -> bytes:
    logger = _approov_logger()
    raw_secret = os.getenv(APPROOV_SECRET_ENV)
    if not _has_text(raw_secret):
        logger.error("Required secret is not set")
        raise RuntimeError("Required secret is not set")

    normalized_secret = raw_secret.strip()
    if normalized_secret == PLACEHOLDER_SECRET:
        logger.error("Required secret is not set")
        raise RuntimeError("Required secret is not set")

    try:
        decoded = _decode_base64url(normalized_secret)
    except (binascii.Error, ValueError):
        logger.error("Required secret is invalid")
        raise RuntimeError("Required secret is invalid")

    if len(decoded) < 32:
        logger.error("Required secret is invalid")
        raise RuntimeError("Required secret is invalid")

    return decoded


def _set_approov_enabled(app: FastAPI, enabled: bool) -> None:
    setattr(app.state, APPROOV_ENABLED_KEY, enabled)


def _is_approov_enabled(app: FastAPI) -> bool:
    return bool(_state_value(app, APPROOV_ENABLED_KEY, True))


def _set_token_binding_enabled(app: FastAPI, enabled: bool) -> None:
    setattr(app.state, TOKEN_BINDING_ENABLED_KEY, enabled)


def _is_token_binding_enabled(app: FastAPI) -> bool:
    return bool(_state_value(app, TOKEN_BINDING_ENABLED_KEY, True))


def _approov_token_header_name(app: FastAPI) -> str:
    return str(_state_value(app, APPROOV_TOKEN_HEADER_KEY, APPROOV_HEADER))


def _approov_secret(app: FastAPI) -> bytes:
    return cast(bytes, _state_value(app, APPROOV_SECRET_KEY))


def _parse_http_port(raw_value: Any, default: int = DEFAULT_HTTP_PORT) -> int:
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        if normalized:
            try:
                return int(normalized)
            except ValueError:
                return default
    return default


def init_approov(app: FastAPI) -> None:
    secret = load_approov_secret()
    setattr(app.state, APPROOV_TOKEN_HEADER_KEY, APPROOV_HEADER)
    setattr(app.state, APPROOV_SECRET_KEY, secret)
    _set_approov_enabled(app, True)
    _set_token_binding_enabled(app, True)


def _get_approov_token_from_request(req: Request) -> Optional[str]:
    target_header = _approov_token_header_name(req.app)
    return req.headers.get(target_header)


def _build_token_binding_string(
    req: Request, bound_headers: list[str]
) -> tuple[Optional[str], Optional[str]]:
    if not bound_headers:
        return "[approov] binding headers not specified", None

    values: list[str] = []
    for header in bound_headers:
        value = req.headers.get(header)
        if not _has_text(value):
            return f"[approov] bound header '{header}' does not exist", None
        values.append(value.strip())

    return None, "".join(values)


def _sha256_b64url_from_str(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _binding_matches(pay_claim: str, computed_hash: str) -> bool:
    return hmac.compare_digest(
        _normalize_base64url(pay_claim), _normalize_base64url(computed_hash)
    )


def _summarize_error(error: str) -> str:
    if error.startswith("[approov] missing ") and error.endswith(" header"):
        return "missing_approov_token"
    if "bound header" in error and "does not exist" in error:
        return "missing_binding_header"
    if "hash mismatch" in error or "does not have a 'pay' claim" in error:
        return "binding_mismatch"
    return "token_verification_failed"


def _required_headers_for_request(req: Request, bound_headers: list[str]) -> list[str]:
    approov_header = _approov_token_header_name(req.app)
    if not bound_headers:
        return [approov_header]
    return [approov_header, *bound_headers]


def _unauthorized_response(req: Request, error: str) -> None:
    req.state.approov_summary = f"approov_failed:{_summarize_error(error)}"
    req.state.approov_error = error
    raise ApproovUnauthorized(error)


def approov(
    req: Request,
    token_check: bool = True,
    bound_headers: Optional[list[str]] = None,
) -> Optional[str]:
    logger = _approov_logger()

    if not token_check or not _is_approov_enabled(req.app):
        logger.warning("[approov] endpoint protection is disabled")
        req.state.approov_claims = {}
        return None

    token = _get_approov_token_from_request(req)
    if not _has_text(token):
        target_header = _approov_token_header_name(req.app)
        return f"[approov] missing {target_header} header"

    try:
        claims = jwt.decode(
            token.strip(),
            _approov_secret(req.app),
            algorithms=["HS256"],
            options={
                "require": ["exp"],
                "verify_signature": True,
                "verify_exp": True,
            },
        )
    except jwt.ExpiredSignatureError:
        return "[approov] token expired"
    except jwt.InvalidSignatureError:
        return "[approov] token signature invalid"
    except jwt.InvalidTokenError as error:
        return f"[approov] token invalid: {error}"

    if bound_headers:
        pay_claim = claims.get("pay")
        if pay_claim is None or (
            isinstance(pay_claim, str) and not _has_text(pay_claim)
        ):
            return "[approov] token does not have a 'pay' claim"
        if not isinstance(pay_claim, str):
            return "[approov] token does not have a valid 'pay' claim"

        binding_error, binding_string = _build_token_binding_string(req, bound_headers)
        if binding_error is not None:
            return binding_error
        if binding_string is None:
            return "[approov] token binding failed"

        computed = _sha256_b64url_from_str(binding_string)
        if not _binding_matches(pay_claim, computed):
            return "[approov] token binding: hash mismatch"

        logger.debug(
            "[approov] token binding verification successful for %s", bound_headers
        )

    req.state.approov_claims = claims
    logger.debug("[approov] token verification successful")
    return None


def require_approov(
    *,
    bound_headers: Optional[Iterable[str]] = None,
) -> Callable[[Request], Awaitable[None]]:
    configured_bound_headers = list(bound_headers or [])

    async def _dependency(req: Request) -> None:
        req.state.approov_error = None

        if not _is_approov_enabled(req.app):
            req.state.approov_summary = "approov_disabled"
            req.state.required_headers = []
            req.state.approov_claims = {}
            return

        active_bound_headers = (
            configured_bound_headers if _is_token_binding_enabled(req.app) else []
        )
        req.state.required_headers = _required_headers_for_request(
            req, active_bound_headers
        )
        error = approov(
            req,
            token_check=True,
            bound_headers=active_bound_headers,
        )
        if error is not None:
            _unauthorized_response(req, error)

        req.state.approov_summary = "approov_ok"

    return _dependency


def state_payload(req: Request) -> dict[str, Any]:
    return {
        "approovEnabled": _is_approov_enabled(req.app),
        "tokenBindingEnabled": _is_token_binding_enabled(req.app),
    }


def info_payload(req: Request, details: str) -> dict[str, Any]:
    body = state_payload(req)
    body["details"] = details
    return body


def _request_server_port(req: Request) -> int:
    server = req.scope.get("server")
    if isinstance(server, tuple) and len(server) > 1:
        parsed_server_port = _parse_http_port(server[1], default=-1)
        if parsed_server_port > 0:
            return parsed_server_port

    return _parse_http_port(os.getenv(HTTP_PORT_ENV), DEFAULT_HTTP_PORT)


def _log_http_request_completed(req: Request, response: Response) -> None:
    if response.status_code not in (200, 401):
        return

    required_headers = getattr(req.state, "required_headers", [])
    summary = getattr(req.state, "approov_summary", "request_completed")
    if response.status_code == 401 and summary == "approov_ok":
        summary = "approov_failed:downstream_unauthorized"

    payload: dict[str, Any] = {
        "summary": summary,
        "method": req.method,
        "path": req.url.path,
        "status": response.status_code,
        "ip": req.client.host if req.client else "",
        "port": _request_server_port(req),
        "approovEnabled": _is_approov_enabled(req.app),
        "tokenBindingEnabled": _is_token_binding_enabled(req.app),
        "required_headers": required_headers,
    }

    error = getattr(req.state, "approov_error", None)
    if error:
        payload["error"] = error

    message = "http.request.completed " + json.dumps(payload, separators=(",", ":"))
    logger = _approov_logger()

    if response.status_code == 401:
        logger.warning(message)
    else:
        logger.info(message)


def create_app() -> FastAPI:
    load_dotenv()
    configure_logging()

    app = FastAPI(title="Approov Backend Quickstart - Python FastAPI")
    init_approov(app)

    def _reset_request_state(req: Request) -> None:
        req.state.required_headers = []
        req.state.approov_summary = "request_completed"
        req.state.approov_error = None

    @app.exception_handler(ApproovUnauthorized)
    async def _approov_unauthorized_handler(
        _request: Request, _error: ApproovUnauthorized
    ) -> JSONResponse:
        return JSONResponse(content={"message": "Unauthorized"}, status_code=401)

    @app.middleware("http")
    async def _request_logging_middleware(
        req: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        _reset_request_state(req)

        response = await call_next(req)
        _log_http_request_completed(req, response)
        return response

    @app.get("/")
    async def home(req: Request) -> dict[str, Any]:
        return info_payload(
            req, f"Approov demo API is running on port {_request_server_port(req)}."
        )

    @app.get("/approov-state")
    async def approov_state(req: Request) -> dict[str, Any]:
        return state_payload(req)

    @app.post("/approov/enable")
    async def enable_approov_endpoint(req: Request) -> dict[str, Any]:
        _set_approov_enabled(req.app, True)
        _set_token_binding_enabled(req.app, True)
        return state_payload(req)

    @app.post("/approov/disable")
    async def disable_approov_endpoint(req: Request) -> dict[str, Any]:
        _set_approov_enabled(req.app, False)
        _set_token_binding_enabled(req.app, False)
        return state_payload(req)

    @app.post("/token-binding/enable")
    async def enable_token_binding_endpoint(req: Request) -> dict[str, Any]:
        _set_token_binding_enabled(req.app, True)
        return state_payload(req)

    @app.post("/token-binding/disable")
    async def disable_token_binding_endpoint(req: Request) -> dict[str, Any]:
        _set_token_binding_enabled(req.app, False)
        return state_payload(req)

    @app.get("/unprotected")
    async def unprotected(req: Request) -> dict[str, Any]:
        return info_payload(
            req,
            "Unprotected endpoint '/unprotected'; no Approov checks performed.",
        )

    @app.get("/token-check", dependencies=[Depends(require_approov())])
    async def token_check(req: Request) -> dict[str, Any]:
        return info_payload(
            req, "Protected endpoint '/token-check'; Approov token verified."
        )

    @app.get(
        "/token-binding",
        dependencies=[Depends(require_approov(bound_headers=[AUTH_HEADER]))],
    )
    async def token_binding(req: Request) -> dict[str, Any]:
        response = info_payload(
            req,
            "Protected endpoint '/token-binding'; Approov token binding enforced.",
        )
        response["authorizationHeaderPresent"] = _has_text(req.headers.get(AUTH_HEADER))
        return response

    @app.get(
        "/token-double-binding",
        dependencies=[
            Depends(require_approov(bound_headers=[AUTH_HEADER, SESSION_ID_HEADER]))
        ],
    )
    async def token_double_binding(req: Request) -> dict[str, Any]:
        response = info_payload(
            req,
            "Protected endpoint '/token-double-binding'; dual token binding enforced.",
        )
        response["authorizationHeaderPresent"] = _has_text(req.headers.get(AUTH_HEADER))
        response["sessionIdHeaderPresent"] = _has_text(
            req.headers.get(SESSION_ID_HEADER)
        )
        return response

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("SERVER_HOSTNAME", "0.0.0.0")
    port = _parse_http_port(os.getenv(HTTP_PORT_ENV), DEFAULT_HTTP_PORT)
    uvicorn.run("ApproovApplication:app", host=host, port=port, reload=False)

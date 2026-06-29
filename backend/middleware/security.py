"""Security middleware: CORS strict, HSTS, security headers."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


def configure_security(app: FastAPI):
    """Apply security hardening to the FastAPI app.

    - CORS: strict origins (never wildcard in production)
    - Security headers: HSTS, X-Frame-Options, X-Content-Type-Options, CSP, etc.
    - Server header removal (CIS 2.5.1 equivalent)
    """
    allowed_origins = [
        "https://app.vivify.com.br",
        "https://api.vivify.com.br",
        "http://localhost:3335",
        "http://localhost:7000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=86400,
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if "server" in response.headers:
            del response.headers["server"]
        return response

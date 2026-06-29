from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .storage.db import init_db
from .api.jewels import router as jewels_router
from .api.certificates import router as certificates_router
from .api.verify import router as verify_router
from .api.simulate import router as simulate_router
from .api.trends import router as trends_router
from .api.defense import router as defense_router
from .api.onboard import router as onboard_router
from .api.competitors import router as competitors_router
from .api.marketplace import router as marketplace_router
from .api.design import router as design_router
from .api.omnichannel import router as omnichannel_router
from .api.subscriptions import router as subscriptions_router
from .api.finances import router as finances_router
from .api.monitoring import router as monitoring_router
from .middleware.subscription_middleware import SubscriptionMiddleware
from .middleware.security import configure_security
from .routes.terminal_routes import router as terminal_router

from .services.scheduler import start_scheduler
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Vivify API", version="0.1.0", lifespan=lifespan)

configure_security(app)
app.add_middleware(SubscriptionMiddleware)

init_db()

# Static files (dashboard frontend)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        from fastapi.responses import FileResponse
        return FileResponse(str(STATIC_DIR / "index.html"))

app.include_router(jewels_router)
app.include_router(certificates_router)
app.include_router(verify_router)
app.include_router(simulate_router)
app.include_router(trends_router)
app.include_router(defense_router)
app.include_router(onboard_router)
app.include_router(competitors_router)
app.include_router(marketplace_router)
app.include_router(design_router)
app.include_router(omnichannel_router)
app.include_router(subscriptions_router)
app.include_router(finances_router)
app.include_router(monitoring_router)
app.include_router(terminal_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "vivify"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=3334, reload=True)

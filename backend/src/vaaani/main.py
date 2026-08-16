import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vaaani.api.routes_health import router as health_router
from vaaani.api.routes_query import router as query_router
from vaaani.config import get_settings
from vaaani.services import ServiceContainer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    services = ServiceContainer.build(settings)
    app.state.services = services
    try:
        await services.initialize()
    except Exception as exc:
        logging.getLogger(__name__).warning("Qdrant initialization deferred: %s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Vaaani API",
        version="0.1.0",
        description="Voice-enabled multilingual retrieval-augmented generation",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(query_router)
    return application


app = create_app()

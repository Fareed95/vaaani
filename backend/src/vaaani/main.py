import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vaaani.api.routes_health import router as health_router
from vaaani.api.routes_query import router as query_router
from vaaani.config import get_settings
from vaaani.services import ServiceContainer

logger = logging.getLogger(__name__)


def _warm_models(services: ServiceContainer) -> None:
    # Touch each lazy-loaded model once so the first real request doesn't pay
    # for a cold sentence-transformers/cross-encoder download+load, which can
    # exceed a platform's request timeout on a fresh container.
    _ = services.encoder.model
    _ = services.nodes.reranker.model
    _ = services.nodes.groundedness.model
    logger.info("Model warm-up complete")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    services = ServiceContainer.build(settings)
    app.state.services = services
    try:
        await services.initialize()
    except Exception as exc:
        logger.warning("Qdrant initialization deferred: %s", exc)
    if settings.enable_ml_models:
        asyncio.create_task(asyncio.to_thread(_warm_models, services))
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

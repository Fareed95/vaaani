from fastapi import APIRouter, Request

from vaaani import __version__
from vaaani.api.schemas import HealthResponse

router = APIRouter(tags=["operations"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    services = request.app.state.services
    count = await services.store.count()
    degraded = services.encoder.degraded or not services.settings.sarvam_api_key
    return HealthResponse(
        status="degraded" if degraded else "healthy",
        version=__version__,
        indexed_chunks=count,
        vector_db="Qdrant",
        languages=services.settings.languages,
    )

from fastapi import APIRouter, Request

from vaaani import __version__
from vaaani.api.schemas import HealthResponse

router = APIRouter(tags=["operations"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    services = request.app.state.services
    settings = services.settings
    count = await services.store.count()
    if settings.voice_provider == "elevenlabs":
        provider_name = "ElevenLabs"
        voice_key_present = bool(settings.elevenlabs_api_keys)
    else:
        provider_name = "Sarvam AI"
        voice_key_present = bool(settings.sarvam_api_key)
    degraded = services.encoder.degraded or not voice_key_present
    return HealthResponse(
        status="degraded" if degraded else "healthy",
        version=__version__,
        indexed_chunks=count,
        vector_db="Qdrant",
        languages=settings.languages,
        stt_provider=provider_name,
        tts_provider=provider_name,
    )

import time

from fastapi import APIRouter, Request

from vaaani import __version__
from vaaani.api.schemas import HealthResponse

router = APIRouter(tags=["operations"])

# An exact Qdrant count is a network round trip and dominates this endpoint
# (~290ms of a ~420ms response). The chunk total only moves on reindex, so a
# short TTL keeps the badge honest without paying for it on every poll.
_COUNT_TTL_SECONDS = 30.0
_count_cache: tuple[float, int] | None = None


async def _indexed_chunks(services) -> int:  # type: ignore[no-untyped-def]
    global _count_cache
    now = time.monotonic()
    if _count_cache and now - _count_cache[0] < _COUNT_TTL_SECONDS:
        return _count_cache[1]
    count = await services.store.count()
    _count_cache = (now, count)
    return count


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    services = request.app.state.services
    settings = services.settings
    count = await _indexed_chunks(services)
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

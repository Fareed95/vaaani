import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from vaaani.api.schemas import QueryRequest, QueryResponse
from vaaani.services import AnswerPreview, EvidencePreview

router = APIRouter(tags=["query"])


async def _token_frames(answer: str):  # type: ignore[no-untyped-def]
    for token in answer.split():
        yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"
        await asyncio.sleep(0.012)


@router.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest, request: Request) -> QueryResponse:
    try:
        return await request.app.state.services.query(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/query/stream")
async def query_stream(payload: QueryRequest, request: Request) -> StreamingResponse:
    async def events():  # type: ignore[no-untyped-def]
        try:
            response: QueryResponse | None = None
            streamed_answer = False
            async for item in request.app.state.services.query_stages(payload):
                if isinstance(item, QueryResponse):
                    response = item
                elif isinstance(item, EvidencePreview):
                    # Retrieval is done and generation hasn't started: send the
                    # citations now so they can be read while the LLM works.
                    evidence = {
                        "transcript": item.transcript,
                        "confidence": item.confidence,
                        "refused": item.refused,
                        "citations": [
                            citation.model_dump(mode="json") for citation in item.citations
                        ],
                    }
                    yield f"event: evidence\ndata: {json.dumps(evidence)}\n\n"
                elif isinstance(item, AnswerPreview):
                    # Groundedness passed, tts hasn't started: the answer can be
                    # read while the audio is still being synthesized.
                    streamed_answer = True
                    async for frame in _token_frames(item.answer):
                        yield frame
                else:
                    yield f"event: stage\ndata: {json.dumps({'stage': item})}\n\n"
            assert response is not None
            metadata = response.model_dump(mode="json", exclude={"answer", "audio_base64"})
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
            if not streamed_answer:
                async for frame in _token_frames(response.answer):
                    yield frame
            if response.audio_base64:
                yield (
                    "event: audio\ndata: "
                    + json.dumps(
                        {"base64": response.audio_base64, "mime_type": response.audio_mime_type}
                    )
                    + "\n\n"
                )
            yield f"event: done\ndata: {json.dumps({'request_id': response.request_id})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

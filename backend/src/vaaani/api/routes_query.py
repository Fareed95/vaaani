import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from vaaani.api.schemas import QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


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
            response = await request.app.state.services.query(payload)
            metadata = response.model_dump(mode="json", exclude={"answer", "audio_base64"})
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
            for token in response.answer.split():
                yield f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"
                await asyncio.sleep(0.012)
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

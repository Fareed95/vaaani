import httpx


class SpeechRecognitionError(RuntimeError):
    pass


class ElevenLabsSTT:
    """Rotates across multiple API keys so one account's exhausted free-tier
    quota (402 payment_required) or revoked key (401) doesn't take the whole
    voice pipeline down — it just moves to the next key in the list."""

    def __init__(self, api_keys: list[str], base_url: str, model: str) -> None:
        self.api_keys = [key for key in api_keys if key]
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def transcribe(self, audio: bytes, mime_type: str, language: str) -> str:
        if not self.api_keys:
            raise SpeechRecognitionError("elevenlabs_api_key_missing")
        base_mime_type = mime_type.split(";")[0].strip() or "audio/webm"
        extension = base_mime_type.split("/")[-1].replace("x-", "") or "webm"
        data = {"model_id": self.model}
        last_error: Exception | None = None
        for key in self.api_keys:
            files = {"file": (f"recording.{extension}", audio, base_mime_type)}
            try:
                async with httpx.AsyncClient(timeout=40) as client:
                    response = await client.post(
                        f"{self.base_url}/speech-to-text",
                        headers={"xi-api-key": key},
                        data=data,
                        files=files,
                    )
                    response.raise_for_status()
                transcript = response.json().get("text", "").strip()
                if not transcript:
                    raise SpeechRecognitionError("elevenlabs_returned_empty_transcript")
                return transcript
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in (401, 402):
                    continue  # this key is exhausted or invalid — try the next one
                raise SpeechRecognitionError(
                    f"elevenlabs_stt_http_error:{exc}:{exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                raise SpeechRecognitionError(f"elevenlabs_stt_http_error:{exc}") from exc
        raise SpeechRecognitionError(f"elevenlabs_all_keys_exhausted:{last_error}")

import httpx


class SpeechRecognitionError(RuntimeError):
    pass


class ElevenLabsSTT:
    def __init__(self, api_key: str | None, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def transcribe(self, audio: bytes, mime_type: str, language: str) -> str:
        if not self.api_key:
            raise SpeechRecognitionError("elevenlabs_api_key_missing")
        base_mime_type = mime_type.split(";")[0].strip() or "audio/webm"
        extension = base_mime_type.split("/")[-1].replace("x-", "") or "webm"
        data = {"model_id": self.model}
        files = {"file": (f"recording.{extension}", audio, base_mime_type)}
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.post(
                    f"{self.base_url}/speech-to-text",
                    headers={"xi-api-key": self.api_key},
                    data=data,
                    files=files,
                )
                response.raise_for_status()
            transcript = response.json().get("text", "").strip()
            if not transcript:
                raise SpeechRecognitionError("elevenlabs_returned_empty_transcript")
            return transcript
        except httpx.HTTPStatusError as exc:
            raise SpeechRecognitionError(
                f"elevenlabs_stt_http_error:{exc}:{exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise SpeechRecognitionError(f"elevenlabs_stt_http_error:{exc}") from exc

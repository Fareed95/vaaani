import httpx


class SpeechRecognitionError(RuntimeError):
    pass


class SarvamSTT:
    def __init__(self, api_key: str | None, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def transcribe(self, audio: bytes, mime_type: str, language: str) -> str:
        if not self.api_key:
            raise SpeechRecognitionError("sarvam_api_key_missing")
        extension = mime_type.split("/")[-1].split(";")[0].replace("x-", "") or "webm"
        data = {"model": self.model, "language_code": language, "mode": "transcribe"}
        files = {"file": (f"recording.{extension}", audio, mime_type)}
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.post(
                    f"{self.base_url}/speech-to-text",
                    headers={"api-subscription-key": self.api_key},
                    data=data,
                    files=files,
                )
                response.raise_for_status()
            transcript = response.json().get("transcript", "").strip()
            if not transcript:
                raise SpeechRecognitionError("sarvam_returned_empty_transcript")
            return transcript
        except httpx.HTTPError as exc:
            raise SpeechRecognitionError(f"sarvam_stt_http_error:{exc}") from exc

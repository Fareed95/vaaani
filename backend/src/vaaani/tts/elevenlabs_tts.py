import base64

import httpx


class SpeechSynthesisError(RuntimeError):
    pass


class ElevenLabsTTS:
    def __init__(self, api_key: str | None, base_url: str, model: str, voice_id: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.voice_id = voice_id

    async def synthesize(self, text: str, language: str) -> tuple[str, str]:
        if not self.api_key:
            raise SpeechSynthesisError("elevenlabs_api_key_missing")
        # eleven_multilingual_v2 detects the target language from the text itself,
        # unlike Sarvam which needs an explicit target_language_code.
        payload = {"text": text[:5000], "model_id": self.model}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{self.voice_id}",
                    headers={"xi-api-key": self.api_key, "content-type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
            if not response.content:
                raise SpeechSynthesisError("elevenlabs_returned_no_audio")
            return base64.b64encode(response.content).decode("ascii"), "audio/mpeg"
        except httpx.HTTPStatusError as exc:
            raise SpeechSynthesisError(
                f"elevenlabs_tts_http_error:{exc}:{exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise SpeechSynthesisError(f"elevenlabs_tts_http_error:{exc}") from exc

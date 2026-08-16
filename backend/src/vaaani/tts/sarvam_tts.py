import httpx


class SpeechSynthesisError(RuntimeError):
    pass


class SarvamTTS:
    def __init__(self, api_key: str | None, base_url: str, model: str, speaker: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.speaker = speaker

    async def synthesize(self, text: str, language: str) -> tuple[str, str]:
        if not self.api_key:
            raise SpeechSynthesisError("sarvam_api_key_missing")
        payload = {
            "text": text[:2400],
            "target_language_code": language,
            "speaker": self.speaker,
            "model": self.model,
            "pace": 1.0,
            "speech_sample_rate": 24000 if self.model == "bulbul:v3" else 22050,
        }
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech",
                    headers={
                        "api-subscription-key": self.api_key,
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            audios = response.json().get("audios", [])
            if not audios:
                raise SpeechSynthesisError("sarvam_returned_no_audio")
            return str(audios[0]), "audio/wav"
        except httpx.HTTPError as exc:
            raise SpeechSynthesisError(f"sarvam_tts_http_error:{exc}") from exc

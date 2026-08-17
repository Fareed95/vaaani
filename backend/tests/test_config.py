from vaaani.config import Settings


def test_csv_env_vars_parse_into_lists(monkeypatch):
    """Regression test: pydantic-settings 2.x JSON-decodes complex-typed env vars
    before field validators run, so a real .env with VAAANI_LANGUAGES=en,hi,bn
    used to crash with SettingsError instead of splitting on commas.
    """
    monkeypatch.setenv("VAAANI_LANGUAGES", "en,hi,bn")
    monkeypatch.setenv("VAAANI_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

    settings = Settings(_env_file=None)

    assert settings.languages == ["en", "hi", "bn"]
    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:3001"]

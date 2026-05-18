from __future__ import annotations

from pathlib import Path
from typing import Any


class SettingsService:
    def __init__(self, base_dir: Path) -> None:
        self._env_path = base_dir / ".env"

    def get_gemini_status(self, config: dict[str, Any]) -> dict[str, Any]:
        api_key = (config.get("GEMINI_API_KEY") or "").strip()
        model = (config.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()
        configured = bool(api_key)
        return {
            "configured": configured,
            "provider": "Gemini API" if configured else "Local Simulation",
            "model": model,
            "masked_key": self._mask_key(api_key),
            "status_text": (
                "Gemini siap dipakai untuk chatbot dan legal brief."
                if configured
                else "API key belum diisi. Sistem memakai fallback lokal tertutup."
            ),
        }

    def save_gemini_settings(self, config: dict[str, Any], api_key: str, model: str | None = None) -> dict[str, Any]:
        normalized_key = api_key.strip()
        normalized_model = (model or config.get("GEMINI_MODEL") or "gemini-2.0-flash").strip()
        if not normalized_key:
            raise ValueError("API key Gemini wajib diisi.")

        self._upsert_env_value("GEMINI_API_KEY", normalized_key)
        self._upsert_env_value("GEMINI_MODEL", normalized_model)

        config["GEMINI_API_KEY"] = normalized_key
        config["GEMINI_MODEL"] = normalized_model
        return self.get_gemini_status(config)

    def _upsert_env_value(self, key: str, value: str) -> None:
        lines: list[str] = []
        if self._env_path.exists():
            lines = self._env_path.read_text(encoding="utf-8").splitlines()

        updated = False
        new_lines: list[str] = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            new_lines.append(f"{key}={value}")

        self._env_path.write_text("\n".join(new_lines).strip() + "\n", encoding="utf-8")

    def _mask_key(self, api_key: str) -> str:
        if not api_key:
            return "Belum diatur"
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return f'{api_key[:4]}...{api_key[-4:]}'

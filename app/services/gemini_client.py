from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request


class GeminiClient:
    def generate_legal_brief(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        scenario: str,
        retrieved_context: list[dict[str, Any]],
        timeout: int = 25,
    ) -> tuple[dict[str, Any] | None, str | None]:
        context_block = self._build_context_block(retrieved_context)
        prompt = (
            "Gunakan konteks regulasi berikut sebagai satu-satunya rujukan.\n\n"
            f"KONTEKS REGULASI:\n{context_block}\n\n"
            f"SKENARIO KASUS:\n{scenario}\n\n"
            "Keluarkan JSON valid tanpa markdown code fence dengan struktur:\n"
            "{\n"
            '  "regulations": [{"title": "...", "body": "..."}],\n'
            '  "bap_draft": ["..."],\n'
            '  "trap_questions": ["..."],\n'
            '  "disclaimer": "..."\n'
            "}\n"
            "Pada elemen regulations, title wajib memuat jenis regulasi + nomor/tahun + pasal/ayat. "
            "Body wajib memuat tanggal penetapan jika tersedia dalam konteks, lalu kutipan norma/ayat yang relevan. "
            "Dilarang membuat nomor pasal, tanggal, atau kutipan yang tidak ada pada konteks regulasi. "
            "Seluruh isi wajib menggunakan Bahasa Indonesia hukum formal dan objektif."
        )
        return self._generate_json(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            prompt=prompt,
            timeout=timeout,
        )

    def chat(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        retrieved_context: list[dict[str, Any]],
        timeout: int = 25,
    ) -> tuple[str | None, str | None]:
        context_block = self._build_context_block(retrieved_context)
        prompt = (
            "Jawab sebagai Senior Legal Counsel BI dengan Bahasa Indonesia hukum formal.\n"
            "Keluarkan jawaban dalam format markdown yang rapi, bukan JSON, dengan struktur minimal:\n"
            "## Jawaban Singkat\n"
            "## Dasar Hukum / Rujukan\n"
            "## Analisis\n"
            "## Catatan Kewenangan BI\n\n"
            f"KONTEKS REGULASI:\n{context_block}\n\n"
            f"PERTANYAAN PENGGUNA:\n{user_prompt}\n\n"
            "Jika pada pertanyaan atau konteks terdapat singkatan yang sudah didefinisikan, gunakan definisi tersebut secara eksplisit dan jangan menggantinya dengan makna lain.\n"
            "Pada bagian Dasar Hukum / Rujukan, sebutkan secara eksplisit jenis regulasi, nomor/tahun, tanggal penetapan jika tersedia, pasal/ayat, dan kutipan norma yang relevan. "
            "Jika konteks tidak cukup, nyatakan secara tegas bahwa jawaban dibatasi oleh dokumen rujukan lokal."
        )
        payload, error_message = self._call_api(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            prompt=prompt,
            timeout=timeout,
            response_mime_type="text/plain",
        )
        if error_message:
            return None, error_message
        return self._extract_text(payload), None

    def _generate_json(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        prompt: str,
        timeout: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        payload, error_message = self._call_api(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            prompt=prompt,
            timeout=timeout,
            response_mime_type="application/json",
        )
        if error_message:
            return None, error_message

        raw_text = self._extract_text(payload)
        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None, "Gemini merespons tetapi format JSON tidak valid; sistem memakai fallback lokal."

        if not isinstance(data, dict):
            return None, "Gemini merespons dengan struktur yang tidak dikenali; sistem memakai fallback lokal."
        return data, None

    def _call_api(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        prompt: str,
        timeout: int,
        response_mime_type: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{parse.quote(model)}:generateContent?key={parse.quote(api_key)}"
        )
        body = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 2048,
                "responseMimeType": response_mime_type,
            },
        }
        req = request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload, None
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return None, f"Gemini API error {exc.code}: {detail[:240]}"
        except Exception as exc:
            return None, f"Gagal menghubungi Gemini API: {exc}"

    def _extract_text(self, payload: dict[str, Any] | None) -> str:
        if not payload:
            return ""
        candidates = payload.get("candidates") or []
        if not candidates:
            return ""
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(texts).strip()

    def _build_context_block(self, retrieved_context: list[dict[str, Any]]) -> str:
        return "\n\n".join(
            f'- {item["code"]} | Tanggal: {item.get("issued_date") or "tidak terindeks"} | {item["chapter"]} | {item["article"]}: '
            f'{item.get("clause_text") or item["summary"]}'
            for item in retrieved_context
        )

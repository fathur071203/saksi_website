from __future__ import annotations

from typing import Any


class SearchService:
    def __init__(self, repository) -> None:
        self._repository = repository
        self._term_aliases = {
            "sk sp": "sksp",
            "s k s p": "sksp",
            "standardisasi kompetensi sistem pembayaran": "sksp",
            "standardisasi kompetensi di bidang sistem pembayaran": "sksp",
            "k k s": "kks",
        }

    def query(self, keyword: str) -> list[dict[str, Any]]:
        keyword = self._normalize_text(keyword)
        if not keyword:
            return []

        regulations = self._repository.load("regulations.json")
        glossary = self._repository.load("glossary.json")
        knowledge_chunks = self._repository.load("knowledge_chunks.json")
        experts = [
            self._normalize_expert(expert)
            for expert in self._repository.load("experts.json")
        ]
        results: list[dict[str, Any]] = []

        for note in glossary:
            haystack = " ".join(
                [
                    note.get("code", ""),
                    note.get("title", ""),
                    note.get("summary", ""),
                    note.get("description", ""),
                    " ".join(note.get("aliases", [])),
                    " ".join(note.get("keywords", [])),
                ]
            )
            haystack = self._normalize_text(haystack)
            if keyword in haystack:
                results.append(
                    {
                        "type": "Catatan Istilah",
                        "title": f'{note.get("code", "Istilah")} - {note.get("title", "")}',
                        "subtitle": note.get("summary", ""),
                    }
                )

        for regulation in regulations:
            haystack = " ".join(
                [
                    regulation["code"],
                    regulation["title"],
                    regulation["chapter"],
                    regulation["article"],
                    regulation["summary"],
                    " ".join(regulation["keywords"]),
                ]
            )
            haystack = self._normalize_text(haystack)
            if keyword in haystack:
                results.append(
                    {
                        "type": "Regulasi",
                        "title": f'{regulation["code"]} - {regulation["article"]}',
                        "subtitle": regulation["summary"],
                    }
                )

        for chunk in knowledge_chunks:
            haystack = " ".join(
                [
                    chunk.get("code", ""),
                    chunk.get("title", ""),
                    chunk.get("article", ""),
                    chunk.get("summary", ""),
                    chunk.get("content", ""),
                    " ".join(chunk.get("keywords", [])),
                ]
            )
            haystack = self._normalize_text(haystack)
            if keyword in haystack:
                results.append(
                    {
                        "type": "Knowledge Upload",
                        "title": f'{chunk.get("code", "Dokumen")} - {chunk.get("article", "Chunk")}',
                        "subtitle": chunk.get("summary", ""),
                    }
                )

        for expert in experts:
            haystack = " ".join(
                [
                    expert["name"],
                    expert["unit"],
                    expert["expertise_summary"],
                    expert.get("pangkat", ""),
                    expert.get("nip", ""),
                    expert.get("employment_type", ""),
                ]
                + [badge["topic"] for badge in expert["badges"]]
            )
            haystack = self._normalize_text(haystack)
            if keyword in haystack:
                results.append(
                    {
                        "type": "Pengawas",
                        "title": expert["name"],
                        "subtitle": expert["expertise_summary"],
                    }
                )

        return results[:8]

    def _normalize_text(self, text: str) -> str:
        normalized = str(text).strip().lower()
        normalized = " ".join(normalized.split())
        for source, target in self._term_aliases.items():
            normalized = normalized.replace(source, target)
        return normalized

    def _normalize_expert(self, expert: dict[str, Any]) -> dict[str, Any]:
        pangkat = str(expert.get("pangkat", "")).strip()
        nip = str(expert.get("nip", "")).strip()
        employment_type = str(expert.get("employment_type", "")).strip()
        unit_parts = [part for part in [pangkat, employment_type] if part]
        unit = expert.get("unit") or (" · ".join(unit_parts) if unit_parts else "Data pegawai")

        return {
            "name": expert.get("name", "-"),
            "unit": f"{unit} · NIP {nip}" if nip and "NIP" not in unit else unit,
            "expertise_summary": expert.get("expertise_summary")
            or " ".join(part for part in [pangkat, employment_type, f"NIP {nip}" if nip else ""] if part).strip()
            or "Profil pegawai aktif",
            "badges": [
                {
                    "topic": badge.get("topic", ""),
                    "level": badge.get("level", ""),
                }
                for badge in expert.get("badges", [])
            ],
            "pangkat": pangkat,
            "nip": nip,
            "employment_type": employment_type,
        }

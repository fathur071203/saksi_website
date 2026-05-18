from __future__ import annotations

from statistics import mean
from typing import Any


class DashboardService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_overview(self, topic: str | None = None) -> dict[str, Any]:
        experts = [
            self._normalize_expert(expert)
            for expert in self._repository.load("experts.json")
        ]
        topics = self._repository.load("topics.json")

        filtered = experts
        if topic and topic != "Semua":
            filtered = [
                expert
                for expert in experts
                if any(badge["topic"] == topic for badge in expert["badges"])
            ]

        certification_count = sum(len(expert["badges"]) for expert in experts)
        avg_sla = round(mean(expert["response_sla_minutes"] for expert in experts)) if experts else 0
        litigation_readiness = round(
            sum(1 for expert in experts if expert["status"] == "Available") / max(len(experts), 1) * 100
        )

        return {
            "metrics": {
                "certified_total": certification_count,
                "avg_sla": avg_sla,
                "readiness": litigation_readiness,
                "available_count": sum(1 for expert in experts if expert["status"] == "Available"),
            },
            "experts": filtered,
            "topics": topics,
            "active_topic": topic or "Semua",
        }

    def _normalize_expert(self, expert: dict[str, Any]) -> dict[str, Any]:
        badges = [
            {
                "topic": badge.get("topic", ""),
                "level": badge.get("level", ""),
                "awarded_at": badge.get("awarded_at", "-"),
                "description": badge.get("description", ""),
            }
            for badge in expert.get("badges", [])
        ]
        pangkat = str(expert.get("pangkat", "")).strip()
        nip = str(expert.get("nip", "")).strip()
        employment_type = str(expert.get("employment_type", "")).strip()

        return {
            "name": expert.get("name", "-"),
            "unit": expert.get("unit") or self._build_unit_label(pangkat, employment_type, nip),
            "courtroom_hours": int(expert.get("courtroom_hours", 0) or 0),
            "status": expert.get("status", "Available"),
            "expertise_summary": expert.get("expertise_summary")
            or self._build_expertise_summary(pangkat, employment_type, nip),
            "response_sla_minutes": int(expert.get("response_sla_minutes", 0) or 0),
            "badges": badges,
            "pangkat": pangkat,
            "nip": nip,
            "employment_type": employment_type,
        }

    def _build_unit_label(self, pangkat: str, employment_type: str, nip: str) -> str:
        parts = [part for part in [pangkat, employment_type] if part]
        label = " · ".join(parts) if parts else "Data pegawai"
        return f"{label} · NIP {nip}" if nip else label

    def _build_expertise_summary(self, pangkat: str, employment_type: str, nip: str) -> str:
        descriptor = " ".join(part for part in [pangkat, f"({employment_type})" if employment_type else ""] if part).strip()
        if descriptor and nip:
            return f"{descriptor} · NIP {nip}"
        if descriptor:
            return descriptor
        if nip:
            return f"NIP {nip}"
        return "Profil pegawai aktif"

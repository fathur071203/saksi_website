from __future__ import annotations

import html
import random
import re
from typing import Any


PROFANITY_PATTERN = re.compile(
    r"(?i)\b(kontol|memek|bangsat|bajingan|anjing|tolol|goblok|tai|fuck|shit|bitch|brengsek)\b"
)

LEGAL_SUBSTANCE_PATTERN = re.compile(
    r"(?i)\b(pbi|padg|uu|pasal|ayat|ketentuan|peraturan|bank indonesia|kewenangan|underlying|kupva|"
    r"transaksi|identifikasi|verifikasi|kepatuhan|pelaporan|valas|tppu)\b"
)

SCENARIO_PROFILES: dict[str, dict[str, Any]] = {
    "KUPVA": {
        "focus_terms": ["kupva", "underlying", "valas", "identifikasi", "verifikasi", "pelaporan", "mencurigakan", "threshold"],
        "required_concepts": [
            ("dasar_hukum", ["pbi", "padg", "pasal", "ayat"], "Sebut dasar hukum spesifik, idealnya PBI/PADG berikut pasal atau ayat yang relevan."),
            ("underlying", ["underlying", "legalitas", "kewajaran"], "Jelaskan mengapa ketiadaan underlying yang jelas menjadi fokus penilaian kepatuhan BI."),
            ("apuppt", ["pelaporan", "mencurigakan", "threshold", "smurfing"], "Tambahkan aspek pemantauan/pelaporan transaksi mencurigakan dan pola pemecahan transaksi di bawah threshold."),
            ("wewenang_bi", ["kewenangan", "administratif", "pengawasan", "bank indonesia"], "Tegaskan batas kewenangan BI pada ranah pengaturan, pengawasan, dan kepatuhan administratif."),
        ],
    },
    "QRIS": {
        "focus_terms": ["qris", "merchant", "akurasi", "data", "keamanan", "penyelenggara", "operasional"],
        "required_concepts": [
            ("dasar_hukum", ["padg", "pbi", "pasal", "ayat"], "Cantumkan dasar hukum QRIS secara eksplisit berikut pasal/ayat yang terkait."),
            ("merchant", ["merchant", "akurasi", "data"], "Uraikan kewajiban akurasi data merchant dan validitas onboarding merchant."),
            ("keamanan", ["keamanan", "pengendalian", "risiko", "operasional"], "Jelaskan kewajiban keamanan transaksi dan pengendalian operasional penyelenggara."),
            ("wewenang_bi", ["pengawasan", "kewenangan", "bank indonesia"], "Tegaskan posisi BI sebagai regulator/pengawas, bukan pihak yang menetapkan unsur pidana."),
        ],
    },
    "Transfer Dana": {
        "focus_terms": ["transfer", "pjp", "kontrol", "pengendalian", "risiko", "kewenangan", "internal"],
        "required_concepts": [
            ("dasar_hukum", ["pbi", "padg", "pasal", "ayat"], "Awali dengan dasar hukum PJP/transfer dana yang relevan berikut pasal atau ayat."),
            ("kontrol_internal", ["kontrol", "pengendalian", "internal", "risiko"], "Jelaskan bagaimana BI melihat kegagalan kontrol internal dan manajemen risiko penyelenggara."),
            ("fakta_pemeriksaan", ["sengketa", "transfer", "berulang", "pjp"], "Hubungkan jawaban dengan fakta sengketa transfer dana berulang yang sedang diperiksa."),
            ("wewenang_bi", ["kewenangan", "pengawasan", "administratif", "bank indonesia"], "Tegaskan batas kewenangan BI pada pengaturan, pengawasan, dan tindak lanjut administratif."),
        ],
    },
}


class InterrogationService:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_page_payload(self) -> dict[str, Any]:
        scenarios = self._repository.load("interrogation_scenarios.json")
        current = scenarios[0]
        return {
            "scenario": current,
            "scenario_count": len(scenarios),
        }

    def get_next_scenario(self) -> dict[str, Any]:
        scenarios = self._repository.load("interrogation_scenarios.json")
        return random.choice(scenarios)

    def evaluate_answer(self, answer: str, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
        transcript = answer.strip()
        normalized = transcript.lower()
        score = 52
        strengths: list[str] = []
        risks: list[str] = []
        improvement_points: list[str] = []
        detected_terms: list[str] = []
        missing_elements: list[str] = []
        scenario_profile = self._resolve_scenario_profile(scenario)

        if not transcript:
            return {
                "score": 0,
                "verdict": "Tidak Layak Disampaikan",
                "transcript": transcript,
                "highlighted_transcript": self._highlight_transcript(transcript),
                "strengths": [],
                "risks": ["Jawaban kosong sehingga tidak dapat dievaluasi sebagai keterangan ahli."],
                "improvement_points": ["Mulai jawaban dengan norma PBI/PADG yang relevan, lalu jelaskan analisis BI secara objektif."],
                "missing_elements": ["Dasar hukum", "Analisis fakta", "Batas kewenangan BI"],
                "detected_terms": [],
                "coaching_prompt": "Mulai jawaban dengan dasar hukum yang relevan, lalu jelaskan analisis secara objektif dan formal.",
            }

        contains_profanity = bool(PROFANITY_PATTERN.search(transcript))
        has_legal_substance = bool(LEGAL_SUBSTANCE_PATTERN.search(transcript))
        word_count = len(transcript.split())

        if "berdasarkan pbi" in normalized or "berdasarkan padg" in normalized:
            score += 12
            self._add_unique(strengths, "Jawaban merujuk langsung pada dasar hukum formal Bank Indonesia.")
        else:
            self._add_unique(risks, "Belum terlihat kutipan regulasi yang eksplisit; risiko dianggap terlalu umum.")
            self._add_unique(improvement_points, "Masukkan pembuka berupa regulasi yang relevan, misalnya PBI/PADG dan pasal yang menjadi sandaran analisis.")

        if "opini saya" in normalized or "menurut saya" in normalized:
            score -= 18
            self._add_unique(risks, "Terdapat frasa opini personal yang sebaiknya dihindari dalam kesaksian ahli.")
            self._add_unique(improvement_points, "Ganti frasa opini personal dengan rumusan objektif seperti 'berdasarkan ketentuan' atau 'dalam batas kewenangan BI'.")

        if "pasal" in normalized and "ayat" in normalized:
            score += 8
            self._add_unique(strengths, "Struktur jawaban sudah spesifik sampai tingkat pasal dan ayat.")

        if contains_profanity:
            score -= 45
            self._add_unique(risks, "Terdapat bahasa vulgar/tidak pantas yang membuat jawaban tidak layak disampaikan di forum pemeriksaan atau persidangan.")
            self._add_unique(improvement_points, "Hapus seluruh kata yang tidak pantas dan susun ulang jawaban dengan nada formal seperti keterangan ahli di persidangan.")

        if not has_legal_substance:
            score -= 24
            self._add_unique(risks, "Jawaban tidak menunjukkan substansi hukum, norma, atau terminologi pemeriksaan yang relevan dengan kapasitas saksi ahli.")
            self._add_unique(improvement_points, "Masukkan istilah hukum dan pengawasan yang relevan dengan pertanyaan, bukan jawaban umum atau deskriptif semata.")
        else:
            self._add_unique(strengths, "Jawaban sudah menyentuh istilah inti yang relevan dengan konteks regulasi dan kewenangan BI.")

        if word_count < 18:
            score -= 14
            self._add_unique(risks, "Jawaban terlalu singkat untuk menjelaskan reasoning hukum secara komprehensif.")
            self._add_unique(improvement_points, "Tambahkan urutan berpikir yang lengkap: dasar hukum, fakta yang dinilai, analisis BI, lalu batas kewenangan BI.")
        else:
            score += 8
            self._add_unique(strengths, "Narasi cukup lengkap untuk menjelaskan reasoning hukum secara lebih utuh.")

        if word_count <= 3:
            score -= 20
            self._add_unique(risks, "Jawaban sangat pendek dan tidak menunjukkan struktur analisis atau keterangan ahli yang memadai.")

        if any(keyword in normalized for keyword in ["kewenangan", "identifikasi", "verifikasi", "pelaporan", "underlying"]):
            score += 10
            self._add_unique(strengths, "Ada unsur analisis operasional/regulatif yang mendukung penjelasan ahli.")

        if scenario_profile:
            scenario_score_delta, scenario_strengths, scenario_risks, scenario_missing, scenario_improvements, scenario_detected = self._evaluate_scenario_fit(
                normalized,
                scenario_profile,
            )
            score += scenario_score_delta
            for item in scenario_strengths:
                self._add_unique(strengths, item)
            for item in scenario_risks:
                self._add_unique(risks, item)
            for item in scenario_missing:
                self._add_unique(missing_elements, item)
            for item in scenario_improvements:
                self._add_unique(improvement_points, item)
            detected_terms.extend(term for term in scenario_detected if term not in detected_terms)

        if "bank indonesia" in normalized and "kewenangan" in normalized:
            self._add_unique(strengths, "Jawaban sudah membedakan posisi BI sebagai ahli/regulator dengan kewenangan penegak hukum.")

        if "administratif" not in normalized and scenario_profile:
            self._add_unique(improvement_points, "Pertimbangkan menegaskan konsekuensi atau penilaian dalam koridor kepatuhan administratif BI.")

        final_score = max(min(score, 100), 0)
        if final_score >= 82:
            verdict = "Siap Bersaksi"
        elif final_score >= 60:
            verdict = "Perlu Penguatan"
        else:
            verdict = "Tidak Layak Disampaikan"

        coaching_prompt = self._build_coaching_prompt(
            contains_profanity=contains_profanity,
            has_legal_substance=has_legal_substance,
            word_count=word_count,
        )
        highlighted = self._highlight_transcript(transcript)

        return {
            "score": final_score,
            "verdict": verdict,
            "transcript": transcript,
            "highlighted_transcript": highlighted,
            "strengths": strengths,
            "risks": risks or ["Tidak ditemukan red flag mayor dalam struktur jawaban ini."],
            "improvement_points": improvement_points[:4],
            "missing_elements": missing_elements[:4],
            "detected_terms": detected_terms[:6],
            "coaching_prompt": coaching_prompt,
        }

    def _resolve_scenario_profile(self, scenario: dict[str, Any] | None) -> dict[str, Any] | None:
        topic = str((scenario or {}).get("topic") or "").strip()
        if topic and topic in SCENARIO_PROFILES:
            return SCENARIO_PROFILES[topic]

        question = str((scenario or {}).get("question") or "").lower()
        for key, profile in SCENARIO_PROFILES.items():
            if key.lower() in question:
                return profile
        return None

    def _evaluate_scenario_fit(self, normalized: str, profile: dict[str, Any]) -> tuple[int, list[str], list[str], list[str], list[str], list[str]]:
        score_delta = 0
        strengths: list[str] = []
        risks: list[str] = []
        missing: list[str] = []
        improvements: list[str] = []
        detected_terms = [term for term in profile.get("focus_terms", []) if term in normalized]

        if len(detected_terms) >= 3:
            score_delta += 12
            strengths.append(f"Jawaban cukup nyambung dengan fokus skenario karena memuat istilah: {', '.join(detected_terms[:4])}.")
        elif detected_terms:
            score_delta += 4
            strengths.append(f"Jawaban sudah mulai menyentuh fokus skenario melalui istilah: {', '.join(detected_terms[:3])}.")
        else:
            score_delta -= 10
            risks.append("Jawaban belum terlihat menjawab inti skenario yang sedang diuji, sehingga terkesan generik.")
            improvements.append("Pastikan jawaban menyebut langsung isu utama yang sedang ditanyakan dalam skenario, bukan hanya norma umum.")

        for concept_name, tokens, improvement_text in profile.get("required_concepts", []):
            if any(token in normalized for token in tokens):
                score_delta += 5
            else:
                missing.append(self._humanize_concept(concept_name))
                improvements.append(improvement_text)

        if missing:
            risks.append(f"Masih ada elemen penting skenario yang belum muncul: {', '.join(missing[:3])}.")

        return score_delta, strengths, risks, missing, improvements, detected_terms

    def _humanize_concept(self, concept_name: str) -> str:
        labels = {
            "dasar_hukum": "dasar hukum spesifik",
            "underlying": "analisis underlying/legalitas transaksi",
            "apuppt": "pemantauan dan pelaporan transaksi mencurigakan",
            "wewenang_bi": "batas kewenangan BI",
            "merchant": "akurasi data merchant",
            "keamanan": "keamanan/pengendalian operasional",
            "kontrol_internal": "kontrol internal dan manajemen risiko",
            "fakta_pemeriksaan": "keterkaitan jawaban dengan fakta perkara",
        }
        return labels.get(concept_name, concept_name.replace("_", " "))

    def _add_unique(self, bucket: list[str], value: str) -> None:
        if value and value not in bucket:
            bucket.append(value)

    def _build_coaching_prompt(self, *, contains_profanity: bool, has_legal_substance: bool, word_count: int) -> str:
        if contains_profanity:
            return "Hapus seluruh bahasa vulgar. Susun ulang jawaban dengan nada formal, objektif, dan layak untuk forum pemeriksaan maupun persidangan."
        if not has_legal_substance:
            return "Mulai dari dasar hukum yang relevan, sebut norma PBI/PADG atau pasal terkait, lalu jelaskan analisis BI secara objektif."
        if word_count < 18:
            return "Perpanjang jawaban dengan urutan: dasar hukum, fakta yang dinilai, analisis BI, lalu batas kewenangan BI secara tegas."
        return "Pertahankan pembuka pada norma PBI/PADG, lalu tegaskan batas wewenang BI secara objektif dan hindari opini pribadi."

    def _highlight_transcript(self, transcript: str) -> str:
        escaped = html.escape(transcript)
        rules = [
            (r"(?i)\b(kontol|memek|bangsat|bajingan|anjing|tolol|goblok|tai|fuck|shit|bitch|brengsek)\b", "bg-red-500/20 text-red-300 border border-red-500/40 rounded px-1"),
            (r"(?i)(menurut opini saya|menurut saya|opini saya)", "bg-red-500/20 text-red-300 border border-red-500/40 rounded px-1"),
            (r"(?i)(berdasarkan pbi[^,.!?;]*|berdasarkan padg[^,.!?;]*|pasal\s+\d+[^,.!?;]*)", "bg-emerald-500/20 text-emerald-200 border border-emerald-500/40 rounded px-1"),
        ]

        for pattern, css_class in rules:
            escaped = re.sub(pattern, lambda match: f'<span class="{css_class}">{match.group(0)}</span>', escaped)

        return escaped

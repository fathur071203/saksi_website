from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from flask import current_app


class ClosedDomainRagService:
    def __init__(self, repository, gemini_client) -> None:
        self._repository = repository
        self._gemini_client = gemini_client
        self._term_aliases = {
            "sk sp": "sksp",
            "s k s p": "sksp",
            "standardisasi kompetensi sistem pembayaran": "sksp",
            "standardisasi kompetensi di bidang sistem pembayaran": "sksp",
            "k k s": "kks",
            "keamanan sistem informasi dan ketahanan siber": "kks",
        }
        self._system_prompt = (
            "Anda adalah Senior Legal Counsel dan Ahli Hukum Sistem Pembayaran Bank Indonesia tingkat eksekutif. "
            "Gunakan Bahasa Indonesia hukum formal yang objektif, presisi, dan bebas asumsi. "
            "Dilarang memfabrikasi regulasi; setiap argumentasi harus bertumpu pada dokumen rujukan lokal."
        )

    def build_grounded_sample_case(self) -> dict[str, Any]:
        regulations = self._load_knowledge_entries()
        prompt = (
            "kupva valas underlying transaksi mencurigakan pelaporan pengawasan bank indonesia "
            "pasal ayat pbi padg kewenangan ahli"
        )
        matches = self._retrieve_relevant_context(prompt, regulations)
        return {
            "scenario": self._build_sample_case_text(matches),
            "references": [self._format_reference_line(item) for item in matches],
            "provider": "Grounded Local RAG",
            "provider_status": "Contoh kasus disusun dari regulasi yang tersedia di knowledge base lokal.",
        }

    def build_brief(self, scenario: str) -> dict[str, Any]:
        regulations = self._load_knowledge_entries()
        top_matches = self._retrieve_relevant_context(scenario, regulations)
        payload = {
            "system_prompt": self._system_prompt,
            "retrieval_architecture": {
                "ingestion": "DHK melakukan chunking poin PBI/PADG dan menyimpannya ke basis data JSON lokal tertutup.",
                "retrieval": "Mesin Flask menilai relevansi berdasarkan kata kunci skenario dan metadata regulasi yang sudah dinormalisasi.",
                "generation": "Konteks regulasi lokal diinjeksikan ke persona Senior Legal Counsel untuk menyusun draft jawaban BAP terstruktur.",
            },
            "regulations": [
                {
                    "title": self._build_regulation_title(item),
                    "body": self._build_regulation_body(item),
                }
                for item in top_matches
            ],
            "bap_draft": self._build_bap_points(scenario, top_matches),
            "trap_questions": self._build_trap_questions(top_matches),
            "disclaimer": (
                "Catatan Ahli: Ahli dari Bank Indonesia hanya berwenang memberikan keterangan mengenai "
                "standar kepatuhan, pengaturan, dan pengawasan sistem pembayaran/kegiatan yang menjadi ranah BI, "
                "serta tidak dalam kapasitas menetapkan terpenuhinya unsur pidana oleh subjek yang diperiksa."
            ),
        }
        return self._apply_gemini_if_available(payload, scenario, top_matches)

    def chat(self, prompt: str) -> dict[str, Any]:
        regulations = self._load_knowledge_entries()
        top_matches = self._retrieve_relevant_context(prompt, regulations)
        top_matches = self._refine_matches_for_prompt(prompt, regulations, top_matches)
        api_key = (current_app.config.get("GEMINI_API_KEY") or "").strip()
        model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
        timeout = current_app.config.get("GEMINI_TIMEOUT", 25)

        if api_key:
            reply, error_message = self._gemini_client.chat(
                api_key=api_key,
                model=model,
                system_prompt=self._system_prompt,
                user_prompt=self._augment_prompt_with_term_notes(prompt, top_matches),
                retrieved_context=top_matches,
                timeout=timeout,
            )
            if reply:
                return {
                    "reply": self._normalize_chat_reply(reply, prompt, top_matches),
                    "citations": self._build_citations(top_matches),
                    "provider": "Gemini API",
                    "provider_status": f"Live via {model}",
                }

        return {
            "reply": self._build_local_chat_reply(prompt, top_matches),
            "citations": self._build_citations(top_matches),
            "provider": "Local Simulation",
            "provider_status": "Fallback RAG lokal aktif",
        }

    def _apply_gemini_if_available(
        self,
        payload: dict[str, Any],
        scenario: str,
        top_matches: list[dict[str, Any]],
    ) -> dict[str, Any]:
        api_key = (current_app.config.get("GEMINI_API_KEY") or "").strip()
        model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
        timeout = current_app.config.get("GEMINI_TIMEOUT", 25)

        if not api_key:
            payload["provider"] = "Local Simulation"
            payload["provider_status"] = "API key Gemini belum diisi; menggunakan closed-domain fallback."
            return payload

        gemini_payload, error_message = self._gemini_client.generate_legal_brief(
            api_key=api_key,
            model=model,
            system_prompt=self._system_prompt,
            scenario=scenario,
            retrieved_context=top_matches,
            timeout=timeout,
        )

        if not gemini_payload:
            payload["provider"] = "Local Simulation"
            payload["provider_status"] = error_message or "Gemini tidak merespons; fallback lokal dipakai."
            return payload

        gemini_bap = gemini_payload.get("bap_draft") or []
        if self._has_explicit_citation(gemini_bap):
            payload["bap_draft"] = gemini_bap

        gemini_traps = gemini_payload.get("trap_questions") or []
        if gemini_traps:
            payload["trap_questions"] = gemini_traps

        payload["disclaimer"] = gemini_payload.get("disclaimer") or payload["disclaimer"]
        payload["provider"] = "Gemini API"
        payload["provider_status"] = f"Generated live via {model}"
        return payload

    def _retrieve_relevant_context(self, scenario: str, regulations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = self._normalize_query_text(scenario)
        tokens = self._tokenize_query(normalized)
        token_counts = Counter(tokens)
        deadline_terms = {"deadline", "tenggat", "jatuh tempo", "batas waktu", "paling lambat", "hari kerja"}
        asks_deadline = any(term in normalized for term in deadline_terms)
        asks_sksp = "sksp" in normalized

        scored: list[tuple[int, dict[str, Any]]] = []
        for item in regulations:
            haystack = " ".join(
                [
                    item["code"],
                    item["title"],
                    item["chapter"],
                    item["article"],
                    item["summary"],
                    item.get("issued_date", ""),
                    item.get("clause_text", ""),
                    item.get("content", ""),
                    " ".join(item.get("aliases", [])),
                ]
                + item["keywords"]
            )
            haystack = self._normalize_query_text(haystack)
            score = sum(count for token, count in token_counts.items() if token in haystack)
            if item.get("source_category") == "core-regulation":
                score += 5
            if item.get("source_category") == "glossary":
                score += 8
            if item["code"].lower().startswith(("pbi", "padg")):
                score += 3
            if item["article"].lower().startswith("pasal"):
                score += 3
            if item["article"].lower().startswith("chunk"):
                score -= 1
            if asks_deadline and any(term in haystack for term in deadline_terms):
                score += 10
            if asks_sksp and any(term in haystack for term in ["sksp", "sertifikat kompetensi sistem pembayaran", "pelaporan sksp"]):
                score += 16
            if asks_sksp and item.get("source_category") == "glossary":
                score += 20
            if asks_sksp and "laporan pelaksanaan sksp" in haystack:
                score += 18
            if asks_sksp and asks_deadline and any(term in haystack for term in ["pasal 12", "pasal 13", "pasal 15"]):
                score += 18
            if score:
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        if scored:
            return [item for _, item in scored[:3]]
        return regulations[:3]

    def _refine_matches_for_prompt(
        self,
        prompt: str,
        regulations: list[dict[str, Any]],
        initial_matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_prompt = self._normalize_query_text(prompt)
        if "sksp" not in normalized_prompt:
            return initial_matches

        if any(term in normalized_prompt for term in ["deadline", "tenggat", "batas waktu", "jatuh tempo", "paling lambat"]):
            focused_prompt = (
                "sksp laporan pelaksanaan sksp pasal 12 pasal 13 pasal 15 "
                "batas waktu paling lambat hari kerja"
            )
            focused_matches = self._retrieve_relevant_context(focused_prompt, regulations)
            if focused_matches:
                return focused_matches

        return initial_matches

    def _load_knowledge_entries(self) -> list[dict[str, Any]]:
        regulations = self._repository.load("regulations.json")
        glossary = self._repository.load("glossary.json")
        uploaded_chunks = self._repository.load("knowledge_chunks.json")
        glossary_entries = [
            {
                "code": item.get("code", "Istilah"),
                "title": item.get("title", "Catatan Istilah"),
                "chapter": "Catatan Internal",
                "article": "Definisi",
                "summary": item.get("summary", ""),
                "content": item.get("description", ""),
                "clause_text": item.get("description") or item.get("summary") or "",
                "keywords": item.get("keywords", []),
                "aliases": item.get("aliases", []),
                "issued_date": "",
                "source_category": "glossary",
            }
            for item in glossary
        ]
        return [self._normalize_entry(item) for item in [*regulations, *glossary_entries, *uploaded_chunks]]

    def _build_bap_points(self, scenario: str, matches: list[dict[str, Any]]) -> list[str]:
        opening = (
            "Sebagai Ahli dari Bank Indonesia, saya menerangkan bahwa penilaian saya berfokus pada norma "
            "kepatuhan dan pengawasan yang diatur dalam regulasi Bank Indonesia yang relevan."
        )
        context_line = (
            "Berdasarkan kronologi yang disampaikan APH, terdapat kebutuhan untuk menilai kesesuaian tata kelola, "
            "pelaporan, dan pengendalian internal penyelenggara terhadap ketentuan BI."
        )
        regulations_line = " ".join(
            f'{self._citation_label(item)} tanggal {self._display_issued_date(item)} menegaskan: "{self._get_clause_text(item).rstrip(".")}". '
            for item in matches
        )
        closing = (
            "Dalam batas kewenangan BI, kesimpulan ahli diarahkan pada ada atau tidaknya deviasi terhadap standar "
            "kepatuhan administratif, sedangkan pembuktian unsur pidana tetap menjadi domain APH."
        )
        scenario_line = f"Konteks yang dinilai: {scenario.strip()}"
        return [opening, context_line, regulations_line.strip(), scenario_line, closing]

    def _build_trap_questions(self, matches: list[dict[str, Any]]) -> list[str]:
        prompts = [
            "Jika ditanya apakah BI menyatakan pelaku pasti melakukan TPPU, jawab bahwa ahli hanya menerangkan standar kepatuhan dan indikator pelanggaran administratif.",
            "Jika didesak memberi opini pribadi, kembali ke rumusan norma pada PBI/PADG dan hindari frase opini individual.",
        ]
        for item in matches[:2]:
            prompts.append(
                f'Apabila pihak lawan meragukan dasar hukum, tegaskan rujukan pada {self._citation_label(item)} dan sebutkan langsung kutipan norma yang relevan terhadap fakta yang diperiksa.'
            )
        return prompts

    def _build_local_chat_reply(self, prompt: str, matches: list[dict[str, Any]]) -> str:
        normalized_prompt = self._normalize_query_text(prompt)
        if "sksp" in normalized_prompt and any(term in normalized_prompt for term in ["deadline", "tenggat", "batas waktu", "jatuh tempo", "paling lambat"]):
            return self._build_sksp_deadline_reply(matches)

        primary = matches[0] if matches else None
        if primary:
            references = [self._format_reference_block(item) for item in matches[:3]]
            short_answer = (
                f'Berdasarkan konteks yang tersedia, isu **{prompt.strip()}** paling dekat dikaitkan dengan '
                f'pengaturan pada **{self._citation_label(primary)}**.'
            )
            analysis = (
                'Dalam perspektif saksi ahli Bank Indonesia, penilaian diarahkan pada kepatuhan normatif, tata kelola, '
                'pelaporan, dan pengawasan administratif yang diatur dalam dokumen rujukan tersebut.'
            )
        else:
            references = ['- Basis pengetahuan lokal belum memuat rujukan yang cukup spesifik untuk pertanyaan ini.']
            short_answer = 'Jawaban dibatasi oleh dokumen rujukan lokal yang saat ini tersedia dalam knowledge base.'
            analysis = 'Diperlukan dokumen tambahan atau perumusan pertanyaan yang lebih spesifik agar analisis dapat lebih presisi.'

        return "\n".join([
            '## Jawaban Singkat',
            short_answer,
            '',
            '## Dasar Hukum / Rujukan',
            *references,
            '',
            '## Analisis',
            f'- Fokus pertanyaan: **{prompt.strip()}**.',
            f'- {analysis}',
            '',
            '## Catatan Kewenangan BI',
            '- Ahli BI menerangkan norma kepatuhan, pengaturan, dan pengawasan dalam ranah Bank Indonesia.',
            '- Penetapan terpenuhinya unsur pidana tetap merupakan kewenangan aparat penegak hukum.',
        ])

    def _build_sksp_deadline_reply(self, matches: list[dict[str, Any]]) -> str:
        references = [self._format_reference_block(item) for item in matches[:3]] or [
            '- Dokumen rujukan lokal mengenai pelaporan SKSP belum cukup lengkap untuk ditampilkan.'
        ]
        return "\n".join([
            '## Jawaban Singkat',
            'Untuk **SKSP (Standardisasi Kompetensi di Bidang Sistem Pembayaran)**, deadline pelaporan **tidak tunggal**; tenggatnya bergantung pada jenis laporan yang disampaikan.',
            '',
            '## Dasar Hukum / Rujukan',
            *references,
            '',
            '## Analisis',
            '- **Laporan triwulanan** mengikuti Pasal 12: paling lambat **10 Hari Kerja pertama** pada bulan April, Juli, Oktober, dan Januari tahun berikutnya sesuai periode data.',
            '- **Laporan tahunan** mengikuti Pasal 13: untuk jenis laporan tertentu batas waktunya **15 Desember tahun berjalan**; untuk jenis tahunan lainnya paling lambat **10 Hari Kerja pertama bulan Januari tahun berikutnya**.',
            '- **Laporan insidental** mengikuti Pasal 15: disampaikan paling lambat **10 Hari Kerja** sejak tanggal penundaan, pencabutan, atau pembatalan penerbitan Sertifikat Kompetensi Sistem Pembayaran.',
            '- Jika yang dimaksud adalah deadline untuk **jenis laporan SKSP tertentu**, maka perlu dibedakan apakah laporannya **triwulanan, tahunan, atau insidental** karena masing-masing memiliki tenggat berbeda.',
            '',
            '## Catatan Kewenangan BI',
            '- Dalam konteks ini, **SKSP/SK SP** dibaca sebagai **Standardisasi Kompetensi di Bidang Sistem Pembayaran**, bukan singkatan lain di luar knowledge base lokal.',
            '- Ahli BI menerangkan norma pelaporan dan kepatuhan administratif berdasarkan dokumen rujukan lokal yang tersedia.',
        ])

    def _normalize_chat_reply(self, raw_reply: str, prompt: str, matches: list[dict[str, Any]]) -> str:
        cleaned = raw_reply.strip()
        parsed_json = self._try_parse_json_reply(cleaned)
        if parsed_json is not None:
            return self._format_json_reply(parsed_json, prompt, matches)

        if '## ' in cleaned or '\n- ' in cleaned or cleaned.startswith('#'):
            return cleaned

        references = [self._format_reference_block(item) for item in matches[:3]] or [
            '- Dokumen rujukan lokal belum cukup spesifik untuk menyusun referensi rinci.'
        ]

        return "\n".join([
            '## Jawaban Singkat',
            cleaned,
            '',
            '## Dasar Hukum / Rujukan',
            *references,
            '',
            '## Catatan Kewenangan BI',
            '- Jawaban ini dibatasi pada norma kepatuhan, pengaturan, dan pengawasan yang menjadi ranah Bank Indonesia.',
            '- Penilaian unsur pidana tetap berada pada kewenangan aparat penegak hukum.',
        ])

    def _try_parse_json_reply(self, raw_reply: str) -> dict[str, Any] | None:
        candidate = raw_reply.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _format_json_reply(self, payload: dict[str, Any], prompt: str, matches: list[dict[str, Any]]) -> str:
        short_answer = payload.get('jawaban') or payload.get('answer') or payload.get('summary') or 'Jawaban belum tersedia.'
        references_value = payload.get('dasar_hukum') or payload.get('references') or payload.get('rujukan') or []
        analysis_value = payload.get('analisis') or payload.get('analysis') or []
        notes_value = payload.get('catatan') or payload.get('notes') or []

        references = self._normalize_section_list(references_value)
        if not references:
            references = [
                self._format_reference_line(item)
                for item in matches[:3]
            ]

        analysis = self._normalize_section_list(analysis_value)
        if not analysis:
            analysis = [f'Fokus pertanyaan yang dibahas: **{prompt.strip()}**.']

        notes = self._normalize_section_list(notes_value)
        if not notes:
            notes = [
                'Ahli BI menerangkan norma kepatuhan, pengaturan, dan pengawasan dalam ranah Bank Indonesia.',
                'Penetapan unsur pidana tetap merupakan kewenangan aparat penegak hukum.',
            ]

        return "\n".join([
            '## Jawaban Singkat',
            str(short_answer).strip(),
            '',
            '## Dasar Hukum / Rujukan',
            *[f'- {item}' for item in references],
            '',
            '## Analisis',
            *[f'- {item}' for item in analysis],
            '',
            '## Catatan Kewenangan BI',
            *[f'- {item}' for item in notes],
        ])

    def _normalize_section_list(self, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, list):
            normalized = []
            for item in value:
                text = str(item).strip()
                if text:
                    normalized.append(text)
            return normalized
        return []

    def _normalize_query_text(self, text: str) -> str:
        normalized = str(text).strip().lower()
        normalized = re.sub(r"\s+", " ", normalized)
        for source, target in self._term_aliases.items():
            normalized = normalized.replace(source, target)
        return normalized

    def _tokenize_query(self, text: str) -> list[str]:
        return [token for token in re.findall(r"[a-z0-9_/.-]+", text) if len(token) > 2]

    def _augment_prompt_with_term_notes(self, prompt: str, matches: list[dict[str, Any]]) -> str:
        term_notes: list[str] = []
        normalized_prompt = self._normalize_query_text(prompt)
        glossary_matches = [item for item in matches if item.get("source_category") == "glossary"]

        for item in glossary_matches[:2]:
            term_notes.append(f'{item["code"]} = {item["title"]}')

        if "sksp" in normalized_prompt and not any(note.startswith("SKSP =") for note in term_notes):
            term_notes.append("SKSP = Standardisasi Kompetensi di Bidang Sistem Pembayaran")
        if "kks" in normalized_prompt and not any(note.startswith("KKS =") for note in term_notes):
            term_notes.append("KKS = Keamanan Siber")

        if not term_notes:
            return prompt

        notes_block = "\n".join(f'- {note}' for note in term_notes)
        return f"CATATAN ISTILAH WAJIB:\n{notes_block}\n\nPERTANYAAN ASLI:\n{prompt.strip()}"

    def _normalize_entry(self, item: dict[str, Any]) -> dict[str, Any]:
        clause_text = str(item.get("clause_text") or item.get("summary") or item.get("content") or "").replace("\n", " ").strip()

        keywords = item.get("keywords") or []
        normalized_keywords = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
        aliases = item.get("aliases") or []
        normalized_aliases = [str(alias).strip() for alias in aliases if str(alias).strip()]

        return {
            **item,
            "code": str(item.get("code") or "Dokumen Tidak Bernama").strip(),
            "title": str(item.get("title") or "Dokumen Regulasi").strip(),
            "chapter": str(item.get("chapter") or "Bagian tidak tersedia").strip(),
            "article": str(item.get("article") or "Pasal tidak tersedia").strip(),
            "summary": str(item.get("summary") or item.get("content") or "Ringkasan belum tersedia.").replace("\n", " ").strip(),
            "content": str(item.get("content") or "").strip(),
            "issued_date": str(item.get("issued_date") or "").strip(),
            "clause_text": clause_text or "Kutipan ayat belum terindeks di basis pengetahuan lokal.",
            "keywords": normalized_keywords,
            "aliases": normalized_aliases,
            "source_category": item.get("source_category") or ("core-regulation" if not item.get("document_id") else "uploaded-chunk"),
        }

    def _build_regulation_title(self, item: dict[str, Any]) -> str:
        return f'{self._citation_label(item)} · {item["title"]}'

    def _build_regulation_body(self, item: dict[str, Any]) -> str:
        return "\n".join([
            f'Jenis / Nomor: {item["code"]}',
            f'Tanggal penetapan: {self._display_issued_date(item)}',
            f'Bagian: {item["chapter"]}',
            f'Pasal / Ayat: {item["article"]}',
            f'Bunyi norma: "{self._get_clause_text(item)}"',
        ])

    def _display_issued_date(self, item: dict[str, Any]) -> str:
        return item.get("issued_date") or "Tanggal penetapan belum terindeks pada basis pengetahuan lokal"

    def _get_clause_text(self, item: dict[str, Any]) -> str:
        return item.get("clause_text") or item.get("summary") or "Kutipan ayat belum tersedia."

    def _citation_label(self, item: dict[str, Any]) -> str:
        return f'{item["code"]}, {item["article"]}'

    def _build_citations(self, matches: list[dict[str, Any]]) -> list[dict[str, str]]:
        citations: list[dict[str, str]] = []
        for item in matches[:3]:
            code = item.get("code", "Dokumen tidak teridentifikasi")
            citations.append(
                {
                    "instrument_type": self._instrument_type(code),
                    "code": code,
                    "number_year": self._extract_number_year(code),
                    "issued_date": self._display_issued_date(item),
                    "article": item.get("article", "Pasal tidak terindeks"),
                    "title": item.get("title", "Judul tidak terindeks"),
                    "quote": self._get_clause_text(item),
                }
            )
        return citations

    def _instrument_type(self, code: str) -> str:
        normalized = str(code).upper()
        if normalized.startswith("PBI"):
            return "PBI"
        if normalized.startswith("PADG"):
            return "PADG"
        if normalized.startswith("SEBI"):
            return "SEBI"
        return "Dokumen Lain"

    def _extract_number_year(self, code: str) -> str:
        match = re.search(r"(\d+[./]\d+[./][A-Z]+[./]\d{4}|\d{4}|\d+/\d+)", str(code), re.IGNORECASE)
        return match.group(1) if match else str(code)

    def _format_reference_block(self, item: dict[str, Any]) -> str:
        return (
            f'- **{self._citation_label(item)}**\n'
            f'  - Judul: {item["title"]}\n'
            f'  - Tanggal penetapan: {self._display_issued_date(item)}\n'
            f'  - Kutipan norma: "{self._get_clause_text(item)}"'
        )

    def _format_reference_line(self, item: dict[str, Any]) -> str:
        return (
            f'**{self._citation_label(item)}** — Judul: {item["title"]} — '
            f'Tanggal penetapan: {self._display_issued_date(item)} — '
            f'Kutipan norma: "{self._get_clause_text(item)}"'
        )

    def _build_sample_case_text(self, matches: list[dict[str, Any]]) -> str:
        if not matches:
            return (
                "Terdapat permintaan keterangan ahli dari APH terkait dugaan pelanggaran kepatuhan sistem pembayaran. "
                "Jelaskan dasar hukum, ruang lingkup pengawasan BI, dan batas kewenangan ahli BI berdasarkan regulasi yang tersedia."
            )

        lead = matches[0]
        support = matches[1:3]
        support_clause = " ".join(
            f"Perhatikan juga {self._citation_label(item)} yang memuat norma: '{self._get_clause_text(item)}'."
            for item in support
        )
        return (
            f"APH meminta keterangan ahli Bank Indonesia mengenai dugaan transaksi yang terkait dengan topik {lead['title']}. "
            f"Susun pendapat ahli dengan titik tolak pada {self._citation_label(lead)} tanggal {self._display_issued_date(lead)}, "
            f"yang menegaskan: '{self._get_clause_text(lead)}'. {support_clause} "
            "Jelaskan dasar hukum, pasal/ayat yang relevan, bunyi norma yang perlu dikutip, analisis BI atas fakta, dan batas kewenangan BI."
        ).strip()

    def _has_explicit_citation(self, lines: list[Any]) -> bool:
        joined = " ".join(str(line) for line in lines)
        normalized = joined.lower()
        return any(token in normalized for token in ["pbi", "padg", "pasal", "ayat"])

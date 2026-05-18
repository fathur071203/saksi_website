# README — Fitur LIVIA (Kontrak Respons)

Dokumen ini khusus menjelaskan **struktur respons** fitur LIVIA agar mudah dipakai/di-brief ke Copilot lain.

## 1) Endpoint yang dipakai

- `GET /livia/` → render halaman UI LIVIA.
- `POST /livia/api/chat` → endpoint utama tanya jawab.

## 2) Request ke LIVIA

**Method:** `POST`  
**Path:** `/livia/api/chat`  
**Content-Type:** `application/json`

Body minimum:

```json
{
  "prompt": "Jelaskan batas kewenangan BI dalam perkara QRIS"
}
```

### Validasi request

- Jika `prompt` kosong/whitespace, server mengembalikan HTTP `400`:

```json
{
  "error": "Pertanyaan untuk Livia wajib diisi."
}
```

## 3) Struktur respons sukses (HTTP 200)

Respons sukses LIVIA selalu berupa objek JSON dengan bentuk berikut:

```json
{
  "assistant_name": "Livia",
  "reply": "...jawaban model...",
  "citations": [
    {
      "instrument_type": "PBI|PADG|SEBI|Dokumen Lain",
      "code": "PBI xx/xx/PBI/xxxx",
      "number_year": "hasil ekstraksi nomor/tahun",
      "issued_date": "tanggal penetapan",
      "article": "Pasal/Ayat",
      "title": "judul regulasi/dokumen",
      "quote": "kutipan norma"
    }
  ],
  "provider": "Gemini API | Local Simulation",
  "provider_status": "status provider (mis. Live via gemini-2.0-flash / Fallback RAG lokal aktif)"
}
```

## 4) Arti tiap field utama

- `assistant_name` *(string)*: saat ini selalu `"Livia"`.
- `reply` *(string)*: jawaban utama yang ditampilkan ke user.
- `citations` *(array)*: maksimal top 3 rujukan regulasi/dokumen relevan.
- `provider` *(string)*:
  - `Gemini API` jika live Gemini berhasil.
  - `Local Simulation` jika fallback lokal dipakai.
- `provider_status` *(string)*: info status detail engine.

## 5) Perilaku fallback

- Jika API key Gemini belum ada / Gemini gagal merespons, endpoint tetap memberi HTTP `200` dengan `provider = "Local Simulation"` dan jawaban dari RAG lokal.
- Jadi, di integrasi Copilot lain, perlakukan fallback sebagai **success response** (bukan error).

## 6) Contoh respons sukses (Gemini)

```json
{
  "assistant_name": "Livia",
  "reply": "Berdasarkan PBI terkait ..., ruang lingkup kewenangan BI meliputi ...",
  "citations": [
    {
      "instrument_type": "PBI",
      "code": "PBI 23/6/PBI/2021",
      "number_year": "23/6",
      "issued_date": "2021-07-01",
      "article": "Pasal 12 ayat (1)",
      "title": "Ketentuan Sistem Pembayaran",
      "quote": "Penyelenggara wajib ..."
    }
  ],
  "provider": "Gemini API",
  "provider_status": "Live via gemini-2.0-flash"
}
```

## 7) Contoh respons sukses (fallback lokal)

```json
{
  "assistant_name": "Livia",
  "reply": "Dalam basis pengetahuan lokal, norma yang relevan adalah ...",
  "citations": [
    {
      "instrument_type": "PADG",
      "code": "PADG 24/10/PADG/2022",
      "number_year": "24/10",
      "issued_date": "2022-05-18",
      "article": "Pasal 15",
      "title": "Pedoman Pengawasan",
      "quote": "Bank Indonesia melakukan pengawasan ..."
    }
  ],
  "provider": "Local Simulation",
  "provider_status": "Fallback RAG lokal aktif"
}
```

## 8) Checklist ringkas untuk Copilot lain

- Kirim `POST /livia/api/chat` dengan body `{ "prompt": "..." }`.
- Tangani `400` hanya untuk validasi prompt kosong.
- Untuk `200`, selalu baca: `reply`, `citations`, `provider`, `provider_status`, `assistant_name`.
- Jangan anggap `provider = Local Simulation` sebagai kegagalan.

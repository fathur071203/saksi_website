from flask import Blueprint, current_app, jsonify, render_template, request

livia_bp = Blueprint("livia", __name__)


@livia_bp.get("/")
def index():
    settings_service = current_app.extensions["services"]["settings"]
    gemini_status = settings_service.get_gemini_status(current_app.config)
    starter_prompts = [
        "Jelaskan batas kewenangan BI dalam perkara KUPVA BB yang dihubungkan dengan TPPU.",
        "Ringkas dasar hukum pengawasan QRIS untuk kebutuhan pemeriksaan APH.",
        "Apa poin pembuka jawaban ahli BI agar objektif dan tidak opini personal?",
        "Dokumen upload mana yang paling relevan untuk isu pengendalian internal PJP?",
    ]
    return render_template(
        "pages/livia.html",
        active_page="livia",
        gemini_status=gemini_status,
        starter_prompts=starter_prompts,
    )


@livia_bp.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "")
    if not prompt.strip():
        return jsonify({"error": "Pertanyaan untuk Livia wajib diisi."}), 400

    service = current_app.extensions["services"]["rag"]
    result = service.chat(prompt)
    result["assistant_name"] = "Livia"
    return jsonify(result)

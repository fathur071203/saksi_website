from flask import Blueprint, current_app, jsonify, render_template, request

legal_bp = Blueprint("legal", __name__)


@legal_bp.get("/")
def index():
    settings_service = current_app.extensions["services"]["settings"]
    document_service = current_app.extensions["services"]["documents"]
    gemini_status = settings_service.get_gemini_status(current_app.config)
    return render_template(
        "pages/legal_generator.html",
        active_page="legal",
        gemini_status=gemini_status,
        documents=document_service.list_documents(),
    )


@legal_bp.post("/api/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    scenario = payload.get("scenario", "")
    if not scenario.strip():
        return jsonify({"error": "Ringkasan kasus wajib diisi."}), 400

    service = current_app.extensions["services"]["rag"]
    return jsonify(service.build_brief(scenario))


@legal_bp.get("/api/sample-case")
def sample_case():
    service = current_app.extensions["services"]["rag"]
    return jsonify(service.build_grounded_sample_case())


@legal_bp.get("/api/settings")
def settings_status():
    settings_service = current_app.extensions["services"]["settings"]
    return jsonify(settings_service.get_gemini_status(current_app.config))


@legal_bp.post("/api/settings")
def save_settings():
    payload = request.get_json(silent=True) or {}
    api_key = payload.get("api_key", "")
    model = payload.get("model", "")
    settings_service = current_app.extensions["services"]["settings"]

    try:
        status = settings_service.save_gemini_settings(current_app.config, api_key, model)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(status)


@legal_bp.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "")
    if not prompt.strip():
        return jsonify({"error": "Pertanyaan chatbot wajib diisi."}), 400

    service = current_app.extensions["services"]["rag"]
    return jsonify(service.chat(prompt))


@legal_bp.get("/api/documents")
def list_documents():
    document_service = current_app.extensions["services"]["documents"]
    return jsonify({"documents": document_service.list_documents()})


@legal_bp.post("/api/documents")
def upload_document():
    uploaded_file = request.files.get("document")
    document_service = current_app.extensions["services"]["documents"]

    try:
        payload = document_service.ingest_upload(uploaded_file)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 201

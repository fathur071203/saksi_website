from flask import Blueprint, current_app, jsonify, render_template
from flask_socketio import emit

from app.core.extensions import socketio

interrogation_bp = Blueprint("interrogation", __name__)


@interrogation_bp.get("/")
def index():
    service = current_app.extensions["services"]["interrogation"]
    payload = service.get_page_payload()
    return render_template("pages/interrogation.html", payload=payload, active_page="interrogation")


@interrogation_bp.get("/api/scenario")
def next_scenario():
    service = current_app.extensions["services"]["interrogation"]
    return jsonify(service.get_next_scenario())


@socketio.on("submit_answer")
def handle_submit_answer(message):
    service = current_app.extensions["services"]["interrogation"]
    answer = (message or {}).get("answer", "")
    scenario = (message or {}).get("scenario") or {}
    feedback = service.evaluate_answer(answer, scenario=scenario)
    emit("transcription_update", {"transcript": feedback["transcript"]})
    emit("feedback_update", feedback)

from flask import Blueprint, current_app, jsonify, render_template, request

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def index():
    topic = request.args.get("topic")
    service = current_app.extensions["services"]["dashboard"]
    payload = service.get_overview(topic)
    return render_template("pages/dashboard.html", payload=payload, active_page="dashboard")


@dashboard_bp.get("/api/experts")
def experts_api():
    topic = request.args.get("topic")
    service = current_app.extensions["services"]["dashboard"]
    return jsonify(service.get_overview(topic))

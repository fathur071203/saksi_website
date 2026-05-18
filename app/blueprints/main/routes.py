from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    experts = current_app.extensions["services"]["dashboard"].get_overview().get("experts", [])
    requested_names = [
        "Saadiah Ludmilla",
        "Tatag Budiarto Anwarudin",
        "Adhityas Ghaniyya Tejo",
    ]
    accent_map = {
        "Saadiah Ludmilla": "from-[#D4AF37] to-[#FADB5F]",
        "Tatag Budiarto Anwarudin": "from-[#003366] to-[#0A192F]",
        "Adhityas Ghaniyya Tejo": "from-[#1E293B] to-[#334155]",
    }
    focus_map = {
        "Saadiah Ludmilla": "Mengawal ketelitian analisis perkara dan kesiapan narasi persidangan.",
        "Tatag Budiarto Anwarudin": "Menjaga ketegasan koordinasi penugasan dan kesiapan operasional tim.",
        "Adhityas Ghaniyya Tejo": "Memperkuat akurasi data, dukungan teknis, dan respons litigasi harian.",
    }
    expert_map = {expert["name"]: expert for expert in experts}
    team_members = []

    for name in requested_names:
        expert = expert_map.get(name)
        if not expert:
            continue
        team_members.append(
            {
                "name": expert["name"],
                "role": expert.get("pangkat") or "Tim SAKSI KPSP",
                "focus": focus_map.get(name, expert.get("expertise_summary", "")),
                "initials": _build_initials(expert["name"]),
                "accent": accent_map.get(name, "from-[#003366] to-[#0A192F]"),
            }
        )

    return render_template(
        "pages/landing.html",
        active_page="landing",
        team_members=team_members,
    )


@main_bp.get("/api/search")
def search():
    keyword = request.args.get("q", "")
    service = current_app.extensions["services"]["search"]
    return jsonify({"results": service.query(keyword)})


@main_bp.get("/health")
def health():
    return jsonify({"status": "ok", "engine": current_app.config["GEMINI_ENGINE_LABEL"]})


def _build_initials(full_name: str) -> str:
    parts = [part for part in full_name.split() if part]
    return "".join(part[0].upper() for part in parts[:2])

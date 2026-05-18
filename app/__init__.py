from flask import Flask

from app.blueprints.competency.routes import competency_bp
from app.blueprints.dashboard.routes import dashboard_bp
from app.blueprints.interrogation.routes import interrogation_bp
from app.blueprints.legal.routes import legal_bp
from app.blueprints.livia.routes import livia_bp
from app.blueprints.main.routes import main_bp
from app.config import Config
from app.core.extensions import socketio
from app.repositories.json_repository import JsonRepository
from app.services.competency_service import CompetencyService
from app.services.dashboard_service import DashboardService
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.gemini_client import GeminiClient
from app.services.interrogation_service import InterrogationService
from app.services.rag_service import ClosedDomainRagService
from app.services.search_service import SearchService
from app.services.settings_service import SettingsService


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    repository = JsonRepository(app.config["DATA_DIR"])
    settings_service = SettingsService(app.config["BASE_DIR"])
    rag_service = ClosedDomainRagService(repository, GeminiClient())
    ingestion_service = DocumentIngestionService(app.config["BASE_DIR"], app.config["DATA_DIR"])

    app.extensions["services"] = {
        "dashboard": DashboardService(repository),
        "documents": ingestion_service,
        "interrogation": InterrogationService(repository),
        "competency": CompetencyService(repository),
        "rag": rag_service,
        "search": SearchService(repository),
        "settings": settings_service,
    }

    app.extensions["document_sync_summary"] = ingestion_service.sync_raw_documents()

    socketio.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(interrogation_bp, url_prefix="/interrogation")
    app.register_blueprint(legal_bp, url_prefix="/legal-brief")
    app.register_blueprint(livia_bp, url_prefix="/livia")
    app.register_blueprint(competency_bp, url_prefix="/competency")

    @app.context_processor
    def inject_shell_context() -> dict:
        gemini_status = settings_service.get_gemini_status(app.config)
        return {
            "app_title": app.config["APP_TITLE"],
            "engine_label": (
                f'{app.config["GEMINI_ENGINE_LABEL"]}: {gemini_status["provider"]}'
                if gemini_status["configured"]
                else f'{app.config["GEMINI_ENGINE_LABEL"]}: Awaiting API Key'
            ),
            "profile_name": app.config["PROFILE_NAME"],
            "profile_role": app.config["PROFILE_ROLE"],
            "profile_badge": app.config["PROFILE_BADGE"],
            "gemini_configured": gemini_status["configured"],
            "supported_document_extensions": sorted(app.config["DOCUMENT_ALLOWED_EXTENSIONS"]),
            "document_sync_summary": app.extensions.get("document_sync_summary", {}),
        }

    return app

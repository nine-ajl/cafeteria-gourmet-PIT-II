"""Application entry point for the Gourmet Coffee Shop."""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from controllers.cafeteria_controller import cafeteria_api
from database import initialize_database
from utils.api_response import api_response


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DATABASE_PATH"] = os.getenv(
        "DATABASE_PATH", str(BASE_DIR / "instance" / "cafeteria.db")
    )
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    initialize_database(app.config["DATABASE_PATH"])
    app.register_blueprint(cafeteria_api)

    @app.get("/")
    def index():
        from flask import render_template

        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(_error):
        return api_response(False, "Recurso não encontrado.", None, 404)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return api_response(False, "Método não permitido para este recurso.", None, 405)

    @app.errorhandler(413)
    def request_too_large(_error):
        return api_response(False, "A requisição excede o tamanho máximo permitido.", None, 413)

    @app.errorhandler(500)
    def internal_error(_error):
        app.logger.exception("Erro interno não tratado.")
        return api_response(
            False, "Ocorreu um erro interno. Tente novamente mais tarde.", None, 500
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    app.run(host="0.0.0.0", port=port, debug=debug)

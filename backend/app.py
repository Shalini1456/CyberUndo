import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from database import db, init_db
from routes import auth_bp, file_bp, share_bp, analytics_bp

# Resolve frontend assets directory path (supports repo root or frontend subdirectory)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
if not os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
    FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "frontend"))
if not os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
    FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

def create_app(config_class=Config):
    """
    Application factory for CyberUndo backend.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing (CORS) for Member 3 Frontend
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize SQLite database and models
    init_db(app)

    # Ensure local upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(file_bp, url_prefix="/api")
    app.register_blueprint(share_bp, url_prefix="/api")
    app.register_blueprint(analytics_bp)  # Handles /api/risk/analyze, /api/blast-radius/analyze, /api/activity/*


    # System Health Check Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "success": True,
            "message": "CyberUndo Backend is running smoothly.",
            "data": {
                "status": "healthy",
                "service": "CyberUndo Backend Core (Member 1)"
            }
        }), 200

    # -------------------------------------------------------------------------
    # Frontend Routes & Static Asset Delivery (Serves CyberUndo UI on Render)
    # -------------------------------------------------------------------------
    @app.route("/", methods=["GET"])
    def serve_frontend_root():
        """Serve the primary CyberUndo Dashboard."""
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/share", methods=["GET"])
    @app.route("/share/<path:subpath>", methods=["GET"])
    def serve_recipient_share_portal(subpath=None):
        """Serve the Recipient Share portal."""
        return send_from_directory(FRONTEND_DIR, "share.html")

    @app.route("/<path:path>", methods=["GET"])
    def serve_static_assets(path):
        """Serve CSS, JS, and static assets, with SPA fallback for client-side routing."""
        # Never intercept /api/* routes
        if path.startswith("api/") or path == "api":
            return jsonify({
                "success": False,
                "message": "API endpoint not found."
            }), 404

        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(FRONTEND_DIR, path)

        # SPA fallback for extensionless routes
        if not os.path.splitext(path)[1]:
            return send_from_directory(FRONTEND_DIR, "index.html")

        return jsonify({
            "success": False,
            "message": "Resource not found"
        }), 404

    # -------------------------------------------------------------------------
    # Consistent JSON Error Handlers
    # -------------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request_error(e):
        return jsonify({
            "success": False,
            "message": getattr(e, "description", "Bad Request")
        }), 400

    @app.errorhandler(401)
    def unauthorized_error(e):
        return jsonify({
            "success": False,
            "message": getattr(e, "description", "Unauthorized access")
        }), 401

    @app.errorhandler(403)
    def forbidden_error(e):
        return jsonify({
            "success": False,
            "message": getattr(e, "description", "Forbidden access")
        }), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return jsonify({
            "success": False,
            "message": getattr(e, "description", "Resource not found")
        }), 404

    @app.errorhandler(405)
    def method_not_allowed_error(e):
        return jsonify({
            "success": False,
            "message": "HTTP method not allowed on this endpoint."
        }), 405

    @app.errorhandler(413)
    def request_entity_too_large(e):
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024) / (1024 * 1024)
        return jsonify({
            "success": False,
            "message": f"File exceeds maximum allowed upload size ({int(max_mb)}MB)."
        }), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({
            "success": False,
            "message": "An internal server error occurred."
        }), 500

    return app


# WSGI application entrypoint for Gunicorn (e.g. gunicorn app:app)
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

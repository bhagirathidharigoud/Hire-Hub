from flask import jsonify

from app.exceptions import HireHubError


def register_error_handlers(app):
    @app.errorhandler(HireHubError)
    def handle_hirehub_error(err):
        return jsonify({"success": False, "message": err.message, "error_code": err.code}), 400

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"success": False, "message": "Resource not found", "error_code": "NOT_FOUND"}), 404

    @app.errorhandler(413)
    def handle_request_too_large(err):
        return jsonify({
            "success": False,
            "message": "Uploaded content exceeds the configured size limit",
            "error_code": "REQUEST_TOO_LARGE",
        }), 413

    @app.errorhandler(500)
    def handle_500(err):
        return jsonify({"success": False, "message": "Server error", "error_code": "INTERNAL_ERROR"}), 500

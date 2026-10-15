"""Helpers for consistently shaped API responses."""

from datetime import datetime, timezone

from flask import jsonify


def api_response(success, message, data=None, status_code=200):
    """Build the standard JSON envelope used by all API endpoints."""
    response = jsonify(
        {
            "success": success,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    response.status_code = status_code
    return response

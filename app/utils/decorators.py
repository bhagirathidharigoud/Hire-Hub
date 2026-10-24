from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                return redirect(url_for("auth.login"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def api_login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Authentication required"}), 401
        return view_func(*args, **kwargs)
    return wrapped


def api_role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                return jsonify({"success": False, "message": "You are not authorized to perform this action"}), 403
            return view_func(*args, **kwargs)
        return wrapped
    return decorator

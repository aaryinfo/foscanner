import traceback

try:
    from gann_app import app
except Exception as e:
    err_msg = traceback.format_exc()
    try:
        from flask import Flask
        app = Flask(__name__)
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def catch_all(path):
            return f"<h1>Vercel Python Crash</h1><pre>{err_msg}</pre>", 500
    except Exception:
        pass

import urllib.parse

from flask import Flask, render_template

from .config import CONFIG_BY_NAME
from .formatting import format_timestamp
from .tools.recent_logs import namespace_prefix
from .tools.rights_log_search import format_params


def create_app(config_name: str = "production") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME.get(config_name, CONFIG_BY_NAME["production"]))

    app.jinja_env.filters["fmt_timestamp"] = format_timestamp
    app.jinja_env.filters["ns_prefix"] = namespace_prefix
    app.jinja_env.filters["fmt_log_params"] = format_params
    app.jinja_env.filters["urlencode"] = lambda s: urllib.parse.quote(s or "")

    from .blueprints.main.routes import main_bp

    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    return app

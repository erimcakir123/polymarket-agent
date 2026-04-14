"""Flask dashboard factory — read-only portfolio monitoring.

Agent ile aynı process'te değil. JSON state dosyalarını okur (logs/positions.json,
logs/trade_history.jsonl). Presentation layer → sadece gösterim.

Memory kuralı (Faz 7): Performance + API usage + AI vs bookmaker bölümleri YOK.
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask

from src.config.settings import AppConfig, load_config
from src.presentation.dashboard.routes import register_routes

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: AppConfig | None = None, logs_dir: Path | str = "logs") -> Flask:
    """Flask uygulamasını oluştur — factory pattern."""
    cfg = config if config is not None else load_config()
    app = Flask(
        __name__,
        template_folder=str(_TEMPLATE_DIR),
        static_folder=str(_STATIC_DIR),
        static_url_path="/static",
    )
    # Dev sırasında tarayıcı cache'ini devre dışı bırak → HTML/CSS/JS değişiklikleri
    # hemen görünsün. ARCH_GUARD Kural 12: presentation concern, burada doğru.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True

    @app.after_request
    def _no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    register_routes(app, cfg, Path(logs_dir))
    return app


def main() -> None:
    """`python -m src.presentation.dashboard.app` için standalone runner."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cfg = load_config()
    app = create_app(cfg)
    app.run(host=cfg.dashboard.host, port=cfg.dashboard.port, debug=False)


if __name__ == "__main__":
    main()

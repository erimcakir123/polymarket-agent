"""Gunicorn giriş noktası: `gunicorn src.presentation.dashboard.wsgi:app`.

Flask dev server (app.run) yerine üretim WSGI sunucusu kullanılır (E3).
"""
from __future__ import annotations

from src.presentation.dashboard.app import create_app

app = create_app()

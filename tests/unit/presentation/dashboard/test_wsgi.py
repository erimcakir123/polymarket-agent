def test_wsgi_app_is_flask():
    from flask import Flask
    from src.presentation.dashboard.wsgi import app
    assert isinstance(app, Flask)

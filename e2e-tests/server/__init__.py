from .app import create_app

__all__ = ['app', 'application']

app = application = create_app()

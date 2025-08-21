# PUBLIC_INTERFACE
def get_app():
    """Return the FastAPI application instance."""
    from .main import app as _app
    return _app

# Expose app at package level for convenience (e.g., uvicorn src.api:app)
from .main import app as app  # noqa: E402,F401

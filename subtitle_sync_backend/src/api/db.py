from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .settings import Settings
from .models import Base


def _build_db_url(settings: Settings) -> str:
    # Do not hardcode credentials; compose from env-provided settings
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def get_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL."""
    url = _build_db_url(settings)
    # pool_pre_ping helps recover from stale connections
    return create_engine(url, pool_pre_ping=True, future=True)


def get_session_maker(engine: Engine):
    """Return a configured sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine: Engine):
    """Initialize database (create tables if they don't exist)."""
    Base.metadata.create_all(bind=engine)

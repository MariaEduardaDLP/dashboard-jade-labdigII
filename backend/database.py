"""Database engine and session setup."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.events import Base


def _normalize_database_url(database_url: str) -> URL:
    normalized_url = database_url.strip()
    if normalized_url.startswith("postgres://"):
        normalized_url = "postgresql://" + normalized_url[len("postgres://"):]

    url = make_url(normalized_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("O backend requer PostgreSQL em JADE_DATABASE_URL.")
    return url.set(drivername="postgresql+psycopg")


def create_database(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    if not database_url:
        raise ValueError("Configure JADE_DATABASE_URL para iniciar o backend.")

    url = _normalize_database_url(database_url)
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    return engine, session_factory

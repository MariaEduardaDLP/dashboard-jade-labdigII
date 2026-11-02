"""Database engine and session setup."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.events import Base


def create_database(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    if not database_url:
        raise ValueError("Configure JADE_DATABASE_URL para iniciar o backend.")

    if make_url(database_url).get_backend_name() != "postgresql":
        raise ValueError("O backend requer PostgreSQL em JADE_DATABASE_URL.")

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    return engine, session_factory

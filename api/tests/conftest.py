"""Test setup: a real PostgreSQL database, migrated with Alembic and seeded from the CSVs.

Set TEST_DATABASE_URL to use an existing database (CI uses a service container).
Otherwise a throwaway PostgreSQL 16 container is started with Testcontainers.
"""

import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent.parent

_container = None
if not os.environ.get("TEST_DATABASE_URL"):
    from testcontainers.postgres import PostgresContainer

    _container = PostgresContainer("postgres:16-alpine", driver="psycopg")
    _container.start()
    os.environ["TEST_DATABASE_URL"] = _container.get_connection_url()

os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["LLM_PROVIDER"] = "rules"
os.environ["STORAGE_BACKEND"] = "local"

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app, get_llm, get_storage  # noqa: E402
from app.schemas import CatalogueIngredient, SkinType  # noqa: E402
from app.seed import seed  # noqa: E402
from app.storage import LocalStorage  # noqa: E402


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _container is not None:
        _container.stop()


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    config.attributes["database_url"] = os.environ["DATABASE_URL"]
    config.attributes["configure_logger"] = False
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    command.upgrade(config, "head")
    with SessionLocal() as db:
        seed(db)


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE products, routines, analyses RESTART IDENTITY CASCADE"))


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@dataclass
class FakeLLM:
    """Scripted LLM: each call pops the next response; a callable builds one from the input."""

    responses: list[str | Exception | Callable[[list[CatalogueIngredient]], str]] = field(
        default_factory=list
    )
    extracted_text: str | Exception = ""
    calls: int = 0

    def explain_raw(self, ingredients: list[CatalogueIngredient], skin_type: SkinType) -> str:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(ingredients)
        return response

    def extract_ingredients(self, image: bytes, mime_type: str) -> str:
        if isinstance(self.extracted_text, Exception):
            raise self.extracted_text
        return self.extracted_text


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(str(tmp_path), "http://testserver")


@pytest.fixture
def client(storage: LocalStorage) -> Iterator[TestClient]:
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_llm] = lambda: None
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def use_llm() -> Callable[[FakeLLM], FakeLLM]:
    def install(fake: FakeLLM) -> FakeLLM:
        app.dependency_overrides[get_llm] = lambda: fake
        return fake

    return install

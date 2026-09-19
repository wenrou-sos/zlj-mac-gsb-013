"""Pytest fixtures: a throwaway SQLite DB and a TestClient."""
import os
import tempfile

import pytest

# configure the DB before importing the app
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.init_db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_database  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # startup event seeds the demo scenario as well
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def reseed():
    """Reset to a clean, freshly seeded demo scenario."""
    db = SessionLocal()
    try:
        db.query(models.Flight).delete()
        db.query(models.RunwayClosure).delete()
        db.commit()
        seed_database(db)
    finally:
        db.close()


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# init tables eagerly even when tests only import fixtures
init_db(seed_if_empty=False)

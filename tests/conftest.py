import os
import tempfile
from pathlib import Path

os.environ["PARTNERSIGNAL_DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp()) / 'test.db'}"
os.environ.pop("PARTNERSIGNAL_ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from partnersignal.db import SessionLocal  # noqa: E402
from partnersignal.main import app  # noqa: E402
from partnersignal.seed import seed  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        with SessionLocal() as session:
            seed(session)
        yield test_client


@pytest.fixture()
def session():
    with SessionLocal() as db:
        seed(db)
        yield db

"""Test setup: a throwaway database and vector store, mock LLM provider."""
import os
import tempfile

# Must be set before any app module is imported
_tmp = tempfile.mkdtemp(prefix="qai-test-")
os.environ["STORAGE_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db".replace("\\", "/")
os.environ["LLM_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import init_db  # noqa: E402
from app.services.knowledge_base import load_knowledge_base  # noqa: E402


@pytest.fixture(scope="session")
def kb():
    init_db()
    return load_knowledge_base()


@pytest.fixture(scope="session")
def client(kb):
    from app.main import app

    with TestClient(app) as c:  # runs the startup (lifespan) code
        yield c

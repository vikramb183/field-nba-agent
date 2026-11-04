import pytest

from app.cache import InMemoryCache
from app.config import get_settings
from app.graph_store import InMemoryGraphStore
from app.workflow import build_workflow


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    """Unit tests never call OpenAI or Redis, even if those env vars are set locally."""
    for var in ("OPENAI_API_KEY", "REDIS_URL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def store():
    return InMemoryGraphStore()


@pytest.fixture
def cache():
    return InMemoryCache()


@pytest.fixture
def workflow(store, cache):
    return build_workflow(store, cache, llm=None, settings=get_settings())

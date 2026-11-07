
import importlib.util

import pytest
import dotenv

import agentfault.database.session as database_session


def test_get_db_yields_session_and_closes_it(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    fake_session = FakeSession()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: fake_session,
    )

    generator = database_session.get_db()

    yielded_session = next(generator)

    assert yielded_session is fake_session
    assert fake_session.closed is False

    with pytest.raises(StopIteration):
        next(generator)

    assert fake_session.closed is True


def test_get_db_closes_session_when_request_raises(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    fake_session = FakeSession()

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        lambda: fake_session,
    )

    generator = database_session.get_db()

    yielded_session = next(generator)

    assert yielded_session is fake_session

    with pytest.raises(RuntimeError, match="Request failed"):
        generator.throw(RuntimeError("Request failed"))

    assert fake_session.closed is True


def test_database_url_missing_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Prevent load_dotenv() from restoring DATABASE_URL.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda: None)

    spec = importlib.util.spec_from_file_location(
        "agentfault.database._session_missing_url_test",
        database_session.__file__,
    )

    module = importlib.util.module_from_spec(spec)

    with pytest.raises(
        RuntimeError,
        match="DATABASE_URL is not configured",
    ):
        spec.loader.exec_module(module)

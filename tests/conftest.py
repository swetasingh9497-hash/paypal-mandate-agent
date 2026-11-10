import pytest
import sqlite3
import tempfile
import os
from fastapi.testclient import TestClient

# Shared test database for all tests
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["DB_PATH"] = _test_db.name
os.environ["MONTHLY_CAP"] = "500"
os.environ["SEED_DEMO"] = "0"

# Create test connection
_test_conn = sqlite3.connect(_test_db.name, check_same_thread=False)
_test_conn.row_factory = sqlite3.Row
_test_conn.execute("PRAGMA foreign_keys = ON")

# Import app after setting up DB
from app.db import set_test_connection, close_db, init_db
init_db(_test_conn)
set_test_connection(_test_conn)

from app.main import app, ORDERS

_client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    """Clear test data before each test."""
    ORDERS.clear()
    _test_conn.execute("DELETE FROM orders")
    _test_conn.execute("DELETE FROM runs")
    _test_conn.commit()
    yield
    _test_conn.execute("DELETE FROM orders")
    _test_conn.execute("DELETE FROM runs")
    _test_conn.commit()


def pytest_sessionfinish(session, exitstatus):
    """Clean up test database after all tests."""
    close_db()
    try:
        os.unlink(_test_db.name)
    except Exception:
        pass


@pytest.fixture
def test_client():
    return _client


@pytest.fixture
def db_conn():
    return _test_conn

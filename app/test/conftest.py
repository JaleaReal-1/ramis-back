import os
os.environ["TESTING"] = "1"

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.connection import get_db
import app.models  # noqa: F401  — tablas de transportes en create_all
from app.main import app

# IMPORTANTE:
# StaticPool hace que TODAS las sesiones usen
# la misma conexión en memoria

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Crear tablas UNA sola vez
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()

    try:
        yield db

    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_db(db_session):

    # Limpiar tablas antes de cada test
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())

    db_session.commit()

    yield


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client():

    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db

        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def mock_current_user_almacenero():
    user = MagicMock()
    user.id = 999
    user.role = "almacenero"
    return user


@pytest.fixture
def mock_current_user_trabajador():
    user = MagicMock()
    user.id = 100
    user.role = "trabajador"
    return user
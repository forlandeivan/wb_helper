from __future__ import annotations

from pathlib import Path

import pytest

from wb_helper.storage.db import create_db_engine, create_session_factory
from wb_helper.storage.repository import RequestRepository


@pytest.fixture()
def repository(tmp_path: Path) -> RequestRepository:
    database_path = tmp_path / "test.db"
    engine = create_db_engine(f"sqlite+pysqlite:///{database_path}")
    session_factory = create_session_factory(engine)
    repository = RequestRepository(session_factory)
    repository.create_schema(engine)
    return repository

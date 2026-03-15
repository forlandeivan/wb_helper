from __future__ import annotations

import os

from rq import Connection, SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from wb_helper.config import Settings
from wb_helper.logging import configure_logging
from wb_helper.queue import create_queue, create_redis
from wb_helper.storage.db import create_db_engine, create_session_factory
from wb_helper.storage.repository import RequestRepository


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.postgres_dsn)
    session_factory = create_session_factory(engine)
    repository = RequestRepository(session_factory)
    if settings.auto_create_schema:
        repository.create_schema(engine)

    redis = create_redis(settings)
    queue = create_queue(settings, redis)

    with Connection(redis):
        worker_class = SimpleWorker if os.name == "nt" else Worker
        worker = worker_class([queue])
        if os.name == "nt":
            worker.death_penalty_class = TimerDeathPenalty
        worker.work()


if __name__ == "__main__":
    main()

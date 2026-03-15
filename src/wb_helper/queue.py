from __future__ import annotations

from redis import Redis
from rq import Queue

from wb_helper.config import Settings


def create_redis(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url)


def create_queue(settings: Settings, connection: Redis | None = None) -> Queue:
    redis_connection = connection or create_redis(settings)
    return Queue(
        name=settings.redis_queue_name,
        connection=redis_connection,
        default_timeout=settings.job_timeout_seconds,
    )


def enqueue_request(queue: Queue, request_id: str, timeout_seconds: int) -> None:
    queue.enqueue(
        "wb_helper.jobs.process_reel_request",
        request_id,
        job_timeout=timeout_seconds,
    )

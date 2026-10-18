from app.workers.celery_app import celery_app


@celery_app.task(name="ufme.ping")
def ping() -> str:
    """Smoke-test task: `celery -A app.workers.celery_app call ufme.ping`."""
    return "pong"

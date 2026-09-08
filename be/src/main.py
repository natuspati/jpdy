import uvicorn

from configs import configure_logging, settings

if __name__ == "__main__":
    configure_logging()
    if settings.workers_count > 1 and not settings.socketio_redis_url:
        raise RuntimeError(
            "BE_SOCKETIO_REDIS_URL is required when BE_WORKERS_COUNT is greater than one",
        )

    uvicorn.run(
        app="application:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers_count,
        reload=settings.reload,
        ws="wsproto",
    )

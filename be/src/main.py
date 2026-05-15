import uvicorn

from configs import configure_logging, settings

if __name__ == "__main__":
    configure_logging()

    uvicorn.run(
        app="application:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers_count,
        reload=settings.reload,
    )

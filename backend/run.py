import os

import uvicorn

from app.config import settings


def main() -> None:
    kwargs = {"host": settings.host, "port": settings.port, "log_level": "info"}
    if settings.ssl_certfile and settings.ssl_keyfile:
        kwargs["ssl_certfile"] = settings.ssl_certfile
        kwargs["ssl_keyfile"] = settings.ssl_keyfile
    uvicorn.run("app.main:app", **kwargs)


if __name__ == "__main__":
    main()
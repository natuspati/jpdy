import pytest

from application import app as asgi_app


@pytest.fixture(scope="session")
def app():
    return asgi_app

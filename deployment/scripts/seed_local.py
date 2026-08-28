#!/usr/bin/env python3
"""Seed a running local Jeopardy API through its public REST endpoints.

Run from ``be/`` so the backend's uv environment is used:

    uv run ../deployment/scripts/seed_local.py

The API must already be healthy. Re-running this script is safe: it keeps the
four fixed users, creates missing seed categories, and reconciles the five
seed categories to their five text prompts. It never creates a lobby or game.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_API_URL: Final = "http://localhost:8000/api/v1"
DEFAULT_HEALTH_URL: Final = "http://localhost:8000/api/health"
REQUEST_TIMEOUT_SECONDS: Final = 10


@dataclass(frozen=True)
class SeedUser:
    label: str
    username: str
    password: str


@dataclass(frozen=True)
class SeedPrompt:
    question: str
    answer: str


@dataclass(frozen=True)
class SeedCategory:
    name: str
    prompts: tuple[SeedPrompt, SeedPrompt, SeedPrompt, SeedPrompt, SeedPrompt]


USERS: Final = (
    SeedUser(label="Host", username="host", password="host123"),
    SeedUser(label="Player", username="alice", password="alice123"),
    SeedUser(label="Player", username="bob", password="bob123"),
    SeedUser(label="Player", username="carol", password="carol123"),
)

CATEGORIES: Final = (
    SeedCategory(
        name="Space",
        prompts=(
            SeedPrompt("What is the largest moon in the Solar System?", "Ganymede"),
            SeedPrompt(
                "What is the nearest major galaxy to the Milky Way?",
                "Andromeda Galaxy",
            ),
            SeedPrompt("Which planet is known as the Red Planet?", "Mars"),
            SeedPrompt("Which planet is famous for its prominent rings?", "Saturn"),
            SeedPrompt("What star is at the center of the Solar System?", "The Sun"),
        ),
    ),
    SeedCategory(
        name="Felids",
        prompts=(
            SeedPrompt("Which big cat has the strongest bite force?", "Jaguar"),
            SeedPrompt("What is the largest living feline species?", "Tiger"),
            SeedPrompt("What is the largest feline that can purr?", "Cheetah"),
            SeedPrompt("Which feline is often called the king of the jungle?", "Lion"),
            SeedPrompt("Which spotted big cat is native to the Americas?", "Jaguar"),
        ),
    ),
    SeedCategory(
        name="World Capitals",
        prompts=(
            SeedPrompt("What is the capital of Japan?", "Tokyo"),
            SeedPrompt("What is the capital of Australia?", "Canberra"),
            SeedPrompt("What is the capital of Canada?", "Ottawa"),
            SeedPrompt("What is the capital of Brazil?", "Brasília"),
            SeedPrompt("What is the capital of Egypt?", "Cairo"),
        ),
    ),
    SeedCategory(
        name="Science Basics",
        prompts=(
            SeedPrompt("What is the chemical formula for water?", "H2O"),
            SeedPrompt("What force keeps planets in orbit around the Sun?", "Gravity"),
            SeedPrompt("What gas do plants take in during photosynthesis?", "Carbon dioxide"),
            SeedPrompt("What is the smallest unit of an element?", "Atom"),
            SeedPrompt("What organ pumps blood through the human body?", "Heart"),
        ),
    ),
    SeedCategory(
        name="Classic Literature",
        prompts=(
            SeedPrompt("Who wrote The Hobbit?", "J. R. R. Tolkien"),
            SeedPrompt("Who created the detective Sherlock Holmes?", "Arthur Conan Doyle"),
            SeedPrompt("Who wrote Pride and Prejudice?", "Jane Austen"),
            SeedPrompt("Who wrote 1984?", "George Orwell"),
            SeedPrompt("Who wrote The Odyssey?", "Homer"),
        ),
    ),
)


class ApiError(RuntimeError):
    """An API request failed or returned an unexpected response."""


class ApiClient:
    def __init__(self, api_url: str) -> None:
        self._api_url = api_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Mapping[str, object] | None = None,
        form_body: Mapping[str, str] | None = None,
        token: str | None = None,
        allowed_error_statuses: Iterable[int] = (),
    ) -> tuple[int, object | None]:
        headers = {"Accept": "application/json"}
        data: bytes | None = None

        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body).encode("utf-8")
        elif form_body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urlencode(form_body).encode("utf-8")

        request = Request(
            url=f"{self._api_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.status, _read_json_response(response.read())
        except HTTPError as error:
            payload = _read_json_response(error.read())
            if error.code in allowed_error_statuses:
                return error.code, payload
            raise ApiError(
                f"{method} {path} failed with HTTP {error.code}: {_error_detail(payload)}",
            ) from error
        except URLError as error:
            raise ApiError(
                f"Could not reach the API at {self._api_url}: {error.reason}",
            ) from error


def _read_json_response(raw_body: bytes) -> object | None:
    if not raw_body:
        return None
    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApiError("API returned a non-JSON response") from error


def _error_detail(payload: object | None) -> str:
    if isinstance(payload, Mapping):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return "unexpected response body"


def _require_object(payload: object | None, description: str) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise ApiError(f"Expected an object while reading {description}")
    return payload


def _require_int(payload: Mapping[str, object], key: str, description: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ApiError(f"Expected integer '{key}' while reading {description}")
    return value


def _require_str(payload: Mapping[str, object], key: str, description: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ApiError(f"Expected non-empty string '{key}' while reading {description}")
    return value


def ensure_api_is_healthy(health_url: str) -> None:
    request = Request(url=health_url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise ApiError(f"Health check returned HTTP {response.status}")
            payload = _require_object(_read_json_response(response.read()), "health check")
    except HTTPError as error:
        raise ApiError(f"Health check failed with HTTP {error.code}") from error
    except URLError as error:
        raise ApiError(f"Could not reach health endpoint {health_url}: {error.reason}") from error

    if payload.get("status") != "healthy":
        raise ApiError(f"Health endpoint {health_url} did not report a healthy API")


def ensure_user(client: ApiClient, user: SeedUser) -> None:
    status, _ = client.request(
        "POST",
        "/user/register",
        json_body={"username": user.username, "password": user.password},
        allowed_error_statuses=(409,),
    )
    action = "created" if status == 201 else "already exists"
    print(f"{user.label} user '{user.username}': {action}")


def sign_in_as_host(client: ApiClient, host: SeedUser) -> str:
    _, payload = client.request(
        "POST",
        "/user/sign-in",
        form_body={"username": host.username, "password": host.password},
    )
    return _require_str(_require_object(payload, "host sign-in"), "access_token", "host sign-in")


def get_host_id(client: ApiClient, token: str) -> int:
    _, payload = client.request("GET", "/user/me", token=token)
    return _require_int(_require_object(payload, "host profile"), "id", "host profile")


def get_host_categories(
    client: ApiClient,
    token: str,
    host_id: int,
) -> dict[str, Mapping[str, object]]:
    query = urlencode((("owner_ids", str(host_id)), ("size", "1000")))
    _, payload = client.request("GET", f"/category?{query}", token=token)
    response = _require_object(payload, "host categories")
    contents = response.get("contents")
    if not isinstance(contents, list):
        raise ApiError("Expected a category list while reading host categories")

    categories: dict[str, Mapping[str, object]] = {}
    for category in contents:
        category_object = _require_object(category, "host category")
        name = _require_str(category_object, "name", "host category")
        categories.setdefault(name, category_object)
    return categories


def ensure_category(
    client: ApiClient,
    token: str,
    category: SeedCategory,
    existing_categories: dict[str, Mapping[str, object]],
) -> None:
    existing = existing_categories.get(category.name)
    if existing is None:
        _, payload = client.request(
            "POST",
            "/category",
            token=token,
            json_body={"name": category.name},
        )
        category_id = _require_int(
            _require_object(payload, f"created category {category.name}"),
            "id",
            f"created category {category.name}",
        )
        prompts: list[Mapping[str, object]] = []
        print(f"Category '{category.name}': created")
    else:
        category_id = _require_int(existing, "id", f"category {category.name}")
        raw_prompts = existing.get("prompts")
        if not isinstance(raw_prompts, list):
            raise ApiError(f"Expected prompts while reading category '{category.name}'")
        prompts = [
            _require_object(prompt, f"prompt in category '{category.name}'")
            for prompt in raw_prompts
        ]
        print(f"Category '{category.name}': reconciling")

    _sync_prompts(client, token, category_id, category, prompts)


def _sync_prompts(
    client: ApiClient,
    token: str,
    category_id: int,
    category: SeedCategory,
    existing_prompts: list[Mapping[str, object]],
) -> None:
    prompts_by_order: dict[int, list[Mapping[str, object]]] = {}
    unordered_prompts: list[Mapping[str, object]] = []
    for prompt in existing_prompts:
        order = prompt.get("order")
        if isinstance(order, int):
            prompts_by_order.setdefault(order, []).append(prompt)
        else:
            unordered_prompts.append(prompt)

    retained_prompts: dict[int, Mapping[str, object]] = {}
    desired_orders = range(1, len(category.prompts) + 1)
    for order in desired_orders:
        candidates = prompts_by_order.pop(order, [])
        if candidates:
            retained_prompts[order] = candidates[0]
            _delete_prompts(client, token, category_id, candidates[1:])

    for extra_prompts in prompts_by_order.values():
        _delete_prompts(client, token, category_id, extra_prompts)
    _delete_prompts(client, token, category_id, unordered_prompts)

    for order, seed_prompt in enumerate(category.prompts, start=1):
        existing = retained_prompts.get(order)
        payload = {
            "question": seed_prompt.question,
            "question_type": "text",
            "answer": seed_prompt.answer,
            "answer_type": "text",
        }
        if existing is None:
            client.request(
                "POST",
                f"/category/{category_id}/prompts",
                token=token,
                json_body={**payload, "order": order},
            )
        else:
            prompt_id = _require_int(
                existing,
                "id",
                f"prompt {order} in category '{category.name}'",
            )
            client.request(
                "PATCH",
                f"/category/{category_id}/prompts/{prompt_id}",
                token=token,
                json_body=payload,
            )


def _delete_prompts(
    client: ApiClient,
    token: str,
    category_id: int,
    prompts: Iterable[Mapping[str, object]],
) -> None:
    for prompt in prompts:
        prompt_id = _require_int(prompt, "id", f"prompt in category {category_id}")
        client.request(
            "DELETE",
            f"/category/{category_id}/prompts/{prompt_id}",
            token=token,
        )


def main() -> int:
    api_url = os.environ.get("JPDY_API_URL", DEFAULT_API_URL)
    health_url = os.environ.get("JPDY_HEALTH_URL", DEFAULT_HEALTH_URL)
    client = ApiClient(api_url)

    try:
        ensure_api_is_healthy(health_url)
        for user in USERS:
            ensure_user(client, user)

        host = USERS[0]
        token = sign_in_as_host(client, host)
        host_id = get_host_id(client, token)
        existing_categories = get_host_categories(client, token, host_id)
        for category in CATEGORIES:
            ensure_category(client, token, category, existing_categories)
    except ApiError as error:
        print(f"Seed failed: {error}", file=sys.stderr)
        return 1

    print("\nSeed complete. No lobby or game was created.")
    print("Host: host / host123")
    print("Players: alice / alice123, bob / bob123, carol / carol123")
    print("Created or reconciled 5 host-owned text categories with 25 prompts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

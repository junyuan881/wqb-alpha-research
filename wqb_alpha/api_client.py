from __future__ import annotations

from typing import Any

import requests

from .auth import BrainAuth
from .config import API_BASE, REQUEST_TIMEOUT_SECONDS


class BrainAPIError(RuntimeError):
    def __init__(self, status_code: int, url: str, message: str, body: str = "") -> None:
        super().__init__(f"HTTP {status_code} {url}: {message}{' | ' + body if body else ''}")
        self.status_code = status_code
        self.url = url
        self.body = body


class BrainClient:
    def __init__(self, auth: BrainAuth | None = None) -> None:
        self.auth = auth or BrainAuth()

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return f"{API_BASE}/{path_or_url.lstrip('/')}"

    def request(self, method: str, path_or_url: str, **kwargs: Any) -> requests.Response:
        url = self._url(path_or_url)
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        response = self.auth.session.request(method.upper(), url, **kwargs)

        if response.status_code == 401:
            self.auth.login(force_relogin=True)
            response = self.auth.session.request(method.upper(), url, **kwargs)

        if response.status_code in (200, 201, 202, 204):
            return response

        body = response.text[:1000] if response.text else ""
        raise BrainAPIError(
            response.status_code,
            url,
            response.reason or "request failed",
            body,
        )

    def get(self, path_or_url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path_or_url, **kwargs)

    def post(self, path_or_url: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path_or_url, **kwargs)

    def patch(self, path_or_url: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path_or_url, **kwargs)

    def delete(self, path_or_url: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path_or_url, **kwargs)

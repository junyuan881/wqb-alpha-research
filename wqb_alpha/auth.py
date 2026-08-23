from __future__ import annotations

import datetime as dt
import getpass
import os
import pickle
from pathlib import Path
from urllib.parse import urljoin

import requests

from .config import API_BASE, SESSION_CACHE, SESSION_CACHE_HOURS, ensure_runtime_directories


class AuthenticationError(RuntimeError):
    pass


def _is_logged_in(response: requests.Response) -> bool:
    """Notebook-compatible success check: HTTP 200/201 and a response body with `user`."""
    if response.status_code not in (200, 201):
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    return isinstance(body, dict) and "user" in body


class BrainAuth:
    """Owns WorldQuant BRAIN login and cached requests.Session state.

    This module does not automate or bypass CAPTCHA, MFA, Persona, or biometric checks.
    If Persona verification is required, interactive mode prints the official verification
    URL and waits for the user to complete the verification manually.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        interactive: bool = True,
        cache_path: str | Path = SESSION_CACHE,
    ) -> None:
        ensure_runtime_directories()
        self.username = username or os.getenv("WQB_USERNAME")
        self.password = password or os.getenv("WQB_PASSWORD")
        self.interactive = interactive
        self.cache_path = Path(cache_path).resolve()
        self._session: requests.Session | None = None
        self.info: dict = {}

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self.login()
        assert self._session is not None
        return self._session

    @property
    def permissions(self) -> list[str]:
        value = self.info.get("permissions", [])
        return list(value) if isinstance(value, list) else []

    def _cache_is_valid(self) -> bool:
        if not self.cache_path.exists():
            return False
        age = dt.datetime.now() - dt.datetime.fromtimestamp(self.cache_path.stat().st_mtime)
        return age < dt.timedelta(hours=SESSION_CACHE_HOURS)

    def _load_cache(self) -> bool:
        if not self._cache_is_valid():
            return False
        try:
            with self.cache_path.open("rb") as f:
                payload = pickle.load(f)
            if isinstance(payload, dict) and "session" in payload:
                self._session = payload["session"]
                self.info = payload.get("info", {})
            else:  # backwards compatibility with the original notebook cache format
                self._session = payload
                self.info = {}
            return isinstance(self._session, requests.Session)
        except Exception:
            return False

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("wb") as f:
            pickle.dump({"session": self._session, "info": self.info}, f)
        try:
            os.chmod(self.cache_path, 0o600)
        except OSError:
            pass

    def clear_cache(self) -> None:
        self.cache_path.unlink(missing_ok=True)
        self._session = None
        self.info = {}

    def login(self, force_relogin: bool = False) -> requests.Session:
        if not force_relogin and self._load_cache():
            assert self._session is not None
            return self._session

        if not (self.username and self.password):
            raise AuthenticationError(
                "請設定 WQB_USERNAME 與 WQB_PASSWORD，或先執行 `python run.py login`。"
            )

        session = requests.Session()
        auth_url = f"{API_BASE}/authentication"
        persona_url = f"{auth_url}/persona"

        response = session.post(
            auth_url,
            auth=(self.username, self.password),
            timeout=30,
        )

        if not _is_logged_in(response):
            try:
                body = response.json()
            except ValueError:
                body = {}

            is_persona = (
                response.status_code == 401
                and (
                    response.headers.get("WWW-Authenticate") == "persona"
                    or (isinstance(body, dict) and "inquiry" in body)
                )
            )
            if not is_persona:
                snippet = response.text[:400] if response.text else ""
                raise AuthenticationError(
                    f"登入失敗 HTTP {response.status_code}: {snippet}"
                )

            location = response.headers.get("Location")
            inquiry = body.get("inquiry", "") if isinstance(body, dict) else ""
            browser_url = (
                urljoin(response.url, location)
                if location
                else f"{persona_url}?inquiry={inquiry}"
            )

            if not self.interactive:
                raise AuthenticationError(
                    "BRAIN 需要 Persona / 生物辨識驗證。請在互動式主程式完成官方驗證："
                    f" {browser_url}"
                )

            print("=" * 72)
            print("BRAIN 需要額外的 Persona / 生物辨識驗證。")
            print("本程式不會自動處理或繞過驗證；請手動開啟官方網址完成驗證：")
            print(f"\n{browser_url}\n")
            print("=" * 72)
            input("完成驗證後按 Enter 繼續... ")

            response = session.post(persona_url, json=body, timeout=30)
            if not _is_logged_in(response):
                response = session.post(browser_url, timeout=30)
            if not _is_logged_in(response):
                snippet = response.text[:400] if response.text else ""
                raise AuthenticationError(
                    f"Persona 驗證未被接受 HTTP {response.status_code}: {snippet}"
                )

        self._session = session
        try:
            self.info = response.json()
        except ValueError:
            self.info = {}
        self._save_cache()
        return session


def prompt_credentials() -> tuple[str, str]:
    username = input("WorldQuant BRAIN email: ").strip()
    password = getpass.getpass("WorldQuant BRAIN password: ")
    os.environ["WQB_USERNAME"] = username
    os.environ["WQB_PASSWORD"] = password
    return username, password


def login_interactively(clear_cache: bool = False) -> BrainAuth:
    username, password = prompt_credentials()
    auth = BrainAuth(username=username, password=password, interactive=True)
    if clear_cache:
        auth.clear_cache()
    auth.login(force_relogin=clear_cache)
    user_id = auth.info.get("user", {}).get("id", "?") if isinstance(auth.info, dict) else "?"
    print(f"登入成功：{user_id}")
    if auth.permissions:
        print("權限：" + ", ".join(auth.permissions))
    return auth


if __name__ == "__main__":
    login_interactively()

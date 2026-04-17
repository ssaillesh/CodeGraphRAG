from __future__ import annotations

import base64
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import requests

from compiler.doc_schema import ConfluencePage, ConfluencePublishResult


class ConfluenceClient:
    def __init__(self, base_url: str, email: str, api_token: str, space_key: str):
        self.base_url = self._normalize_base_url(base_url)
        self.email = email
        self.api_token = api_token
        self.space_key = space_key

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        value = (base_url or "").strip()
        if not value:
            raise ValueError(
                "Confluence base URL is not configured. Set CONFLUENCE_BASE_URL to your site URL, "
                "for example https://your-domain.atlassian.net"
            )

        parsed = urlparse(value)
        if not parsed.scheme:
            value = f"https://{value.lstrip('/')}"
            parsed = urlparse(value)

        if not parsed.netloc:
            raise ValueError(
                f"Invalid Confluence base URL: {base_url!r}. Use the site root, not a page URL. "
                "Example: https://your-domain.atlassian.net"
            )

        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def _headers(self) -> dict:
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        text = (response.text or "").strip()
        if len(text) > 1500:
            text = text[:1500] + "..."
        return f"{response.status_code} {response.reason}: {text}"

    @staticmethod
    def _compact_body(body_storage: str, max_chars: int = 40_000) -> str:
        if len(body_storage) <= max_chars:
            return body_storage
        return body_storage[:max_chars] + "\n<p>Content compacted due to Confluence payload limits.</p>"

    def _find_page_by_title(self, title: str) -> Optional[dict]:
        url = f"{self.base_url}/wiki/rest/api/content"
        params = {
            "spaceKey": self.space_key,
            "title": title,
            "status": "current",
            "expand": "version,status",
        }
        try:
            response = requests.get(url, headers=self._headers(), params=params, timeout=30)
            response.raise_for_status()
            results = response.json().get("results", [])
            for result in results:
                if result.get("status", "current") == "current":
                    return result
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def _resolve_parent_id(self, parent_title: Optional[str]) -> Optional[str]:
        if not parent_title:
            return None
        parent = self._find_page_by_title(parent_title)
        if not parent:
            return None
        return parent["id"]

    def upsert_page(self, page: ConfluencePage) -> ConfluencePublishResult:
        existing = self._find_page_by_title(page.title)
        parent_id = self._resolve_parent_id(page.parent_title)

        if existing:
            return self._update_page(existing, page, parent_id)
        return self._create_page(page, parent_id)

    def _create_page(self, page: ConfluencePage, parent_id: Optional[str]) -> ConfluencePublishResult:
        url = f"{self.base_url}/wiki/rest/api/content"
        payload = {
            "type": "page",
            "title": page.title,
            "space": {"key": self.space_key},
            "body": {"storage": {"value": page.body_storage, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        if response.status_code == 400 and "exists" in response.text.lower():
            # Archived titles can conflict with create; retry with a unique suffix.
            suffix = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            payload["title"] = f"{page.title} ({suffix})"
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)

        if response.status_code == 400:
            # Retry once with compacted content for large/complex repositories.
            payload["body"]["storage"]["value"] = self._compact_body(page.body_storage)
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)

        if not response.ok:
            raise ValueError(
                f"Confluence create failed for '{payload['title']}' at {url}: {self._error_detail(response)}"
            )
        created = response.json()
        return ConfluencePublishResult(title=page.title, page_id=created["id"], status="created")

    def _update_page(
        self,
        existing_page: dict,
        page: ConfluencePage,
        parent_id: Optional[str],
    ) -> ConfluencePublishResult:
        page_id = existing_page["id"]
        version_number = existing_page["version"]["number"] + 1
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
        payload = {
            "id": page_id,
            "type": "page",
            "title": page.title,
            "space": {"key": self.space_key},
            "version": {"number": version_number},
            "body": {"storage": {"value": page.body_storage, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        response = requests.put(url, headers=self._headers(), json=payload, timeout=30)
        if response.status_code == 403:
            # Common when the existing page is archived or edit-restricted; create a new page instead.
            return self._create_page(page, parent_id)

        if response.status_code == 400:
            payload["body"]["storage"]["value"] = self._compact_body(page.body_storage)
            response = requests.put(url, headers=self._headers(), json=payload, timeout=30)

        if not response.ok:
            raise ValueError(
                f"Confluence update failed for page_id={page_id} at {url}: {self._error_detail(response)}"
            )
        return ConfluencePublishResult(title=page.title, page_id=page_id, status="updated")

    def publish_tree(self, pages: list[ConfluencePage]) -> list[ConfluencePublishResult]:
        results = []
        for page in pages:
            results.append(self.upsert_page(page))
        return results

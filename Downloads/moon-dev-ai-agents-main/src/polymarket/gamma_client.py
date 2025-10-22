"""Gamma Markets discovery client (public, read-only).

Functions:
 - get_markets() -> list of markets with id, slug, end_time
 - filter_markets(predicate) -> filtered list

Reads GAMMA_API_BASE from environment or falls back to provided base.
"""
from typing import List, Dict, Any, Callable, Optional
import os
import requests
from datetime import datetime

GAMMA_API_BASE = os.environ.get("GAMMA_API_BASE", "https://gamma-api.polymarket.com").rstrip('/')


class GammaClient:
    def __init__(self, base: Optional[str] = None, session: Optional[requests.Session] = None):
        self.base = (base or GAMMA_API_BASE).rstrip('/')
        self.session = session or requests.Session()

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def get_markets(self) -> List[Dict[str, Any]]:
        """Fetch markets from Gamma API and return a minimal list.

        Returns list of dicts with at least: token_id (id), slug/title, end_time (ISO string).
        """
        url = self._url('/markets')
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        markets = []
        for m in data.get('data', []) if isinstance(data, dict) else (data or []):
            markets.append({
                'id': m.get('id') or m.get('token_id') or m.get('tokenId'),
                'slug': m.get('slug') or m.get('title') or m.get('name'),
                'end_time': m.get('end_time') or m.get('endTime') or m.get('end'),
                'raw': m,
            })
        return markets

    def filter_markets(self, active_only: bool = True, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return markets optionally filtered by active status or tag.

        active_only: filters markets whose end_time is in the future.
        tag: include only markets containing `tag` in their tags/title/slug.
        """
        markets = self.get_markets()
        out = []
        now = datetime.utcnow()
        for m in markets:
            if active_only:
                et = m.get('end_time')
                if et:
                    try:
                        et_dt = datetime.fromisoformat(et.replace('Z', '+00:00'))
                        if et_dt <= now:
                            continue
                    except Exception:
                        pass
            if tag:
                s = (m.get('slug') or '').lower()
                if tag.lower() not in s:
                    continue
            out.append(m)
        return out

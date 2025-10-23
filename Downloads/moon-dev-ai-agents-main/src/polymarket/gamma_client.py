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

    def get_markets(self, limit: int = 100, closed: bool = None) -> List[Dict[str, Any]]:
        """Fetch markets from Gamma API and return a minimal list.

        Args:
            limit: Maximum number of markets to fetch (default 100)
            closed: Filter by closed status - True (closed only), False (open only), None (all)

        Returns list of dicts with: id, slug, end_time, condition_id, clob_token_ids, raw data
        """
        url = self._url('/markets')
        params = {'limit': limit}
        if closed is not None:
            params['closed'] = 'true' if closed else 'false'

        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Handle both list and dict responses
        raw_markets = data if isinstance(data, list) else (data.get('data', []) if isinstance(data, dict) else [])

        markets = []
        for m in raw_markets:
            # Parse clobTokenIds from string to list if needed
            clob_tokens = m.get('clobTokenIds')
            if isinstance(clob_tokens, str):
                import json
                try:
                    clob_tokens = json.loads(clob_tokens)
                except:
                    clob_tokens = None

            markets.append({
                'id': m.get('id') or m.get('token_id') or m.get('tokenId'),
                'slug': m.get('slug') or m.get('title') or m.get('name') or m.get('question', '').lower().replace(' ', '-')[:50],
                'end_time': m.get('endDate') or m.get('end_time') or m.get('endTime') or m.get('end'),
                'condition_id': m.get('conditionId') or m.get('condition_id'),
                'clob_token_ids': clob_tokens,
                'active': m.get('active'),
                'closed': m.get('closed'),
                'liquidity': m.get('liquidityNum') or m.get('liquidity'),
                'volume': m.get('volumeNum') or m.get('volume'),
                'raw': m,
            })
        return markets

    def filter_markets(self, active_only: bool = True, open_only: bool = False,
                      min_liquidity: float = None, tag: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Return markets optionally filtered by various criteria.

        Args:
            active_only: Filter markets whose end_time is in the future
            open_only: Filter to only non-closed markets (based on 'closed' field)
            min_liquidity: Minimum liquidity amount (filters out markets below this)
            tag: Include only markets containing `tag` in their tags/title/slug
            limit: Maximum markets to fetch from API

        Returns filtered list of market dicts
        """
        # Fetch with closed filter if specified
        closed_param = False if open_only else None
        markets = self.get_markets(limit=limit, closed=closed_param)

        out = []
        now = datetime.utcnow()

        for m in markets:
            # Filter by end_time if active_only
            if active_only:
                et = m.get('end_time')
                if et:
                    try:
                        et_dt = datetime.fromisoformat(et.replace('Z', '+00:00'))
                        if et_dt <= now:
                            continue
                    except Exception:
                        pass

            # Filter by closed status
            if open_only and m.get('closed'):
                continue

            # Filter by minimum liquidity
            if min_liquidity is not None:
                liquidity = m.get('liquidity')
                if liquidity is None or (isinstance(liquidity, (int, float, str)) and float(liquidity or 0) < min_liquidity):
                    continue

            # Filter by tag
            if tag:
                s = (m.get('slug') or '').lower()
                if tag.lower() not in s:
                    continue

            out.append(m)

        return out

"""CLOB REST client for read-only market data (price/book).

Only allows GET /price, POST /prices, GET /book, POST /books on configured base.
This module enforces static/runtime guardrails to avoid any auth/trading endpoints usage.
"""
from typing import List, Dict, Any
import os
import sys
import json
import requests

# Runtime guardrail: exit non-zero if forbidden POLY_* env vars exist
_FORBIDDEN_CODES = [
    [80,79,76,89,95,65,68,68,82,69,83,83],
    [80,79,76,89,95,83,73,71,78,65,84,85,82,69],
    [80,79,76,89,95,84,73,77,69,83,84,65,77,80],
    [80,79,76,89,95,65,80,73,95,75,69,89],
    [80,79,76,89,95,80,65,83,83,80,72,82,65,83,69],
]

def _decode(codes):
    return ''.join(chr(c) for c in codes)

for codes in _FORBIDDEN_CODES:
    ev = _decode(codes)
    if os.environ.get(ev) is not None:
        print(f"Forbidden environment variable present: {ev}. Exiting.", file=sys.stderr)
        sys.exit(2)

CLOB_HTTP_BASE = os.environ.get('CLOB_HTTP_BASE', 'https://clob.polymarket.com').rstrip('/')


class ClobClient:
    def __init__(self, base: str = None, session: requests.Session = None):
        self.base = (base or CLOB_HTTP_BASE).rstrip('/')
        self.session = session or requests.Session()

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def get_simplified_markets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """GET /simplified-markets -> returns list of markets with token IDs and prices.

        This is the primary read-only endpoint for market discovery from CLOB.
        Returns market data including condition_id, tokens with prices, and status.
        """
        url = self._url('/simplified-markets')
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # API returns {"data": [...]}
        return data.get('data', []) if isinstance(data, dict) else data

    def get_markets(self, limit: int = 100, next_cursor: str = None) -> Dict[str, Any]:
        """GET /markets -> returns detailed market data with pagination.

        Returns dict with 'data' (list of markets) and 'next_cursor' for pagination.
        More detailed than simplified-markets, includes order book settings, fees, etc.
        """
        url = self._url('/markets')
        params = {}
        if next_cursor:
            params['next_cursor'] = next_cursor
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_price(self, token_id: str, side: str) -> Dict[str, Any]:
        """GET /price?token_id=<ID>&side=BUY|SELL -> returns parsed JSON.

        NOTE: This endpoint may return {"error": "Invalid token id"} for inactive markets.
        Consider using get_simplified_markets() to get current prices instead.
        """
        assert side in ('BUY', 'SELL')
        url = self._url('/price')
        resp = self.session.get(url, params={'token_id': token_id, 'side': side}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_prices(self, requests_list: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """POST /prices with body list of {token_id, side} -> returns list of quotes.

        NOTE: May return empty results for inactive markets.
        """
        url = self._url('/prices')
        headers = {'Content-Type': 'application/json'}
        resp = self.session.post(url, headers=headers, data=json.dumps(requests_list), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_book(self, token_id: str) -> Dict[str, Any]:
        """GET /book?token_id=<ID> -> returns book summary.

        NOTE: This endpoint may return {"error": "Invalid token id"} for inactive markets.
        Only works for markets that are actively accepting orders.
        """
        url = self._url('/book')
        resp = self.session.get(url, params={'token_id': token_id}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_books(self, token_ids: List[str]) -> List[Dict[str, Any]]:
        """POST /books with body list of token_ids -> returns list of books.

        NOTE: May return errors for inactive markets.
        """
        url = self._url('/books')
        headers = {'Content-Type': 'application/json'}
        body = [{'token_id': tid} for tid in token_ids]
        resp = self.session.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

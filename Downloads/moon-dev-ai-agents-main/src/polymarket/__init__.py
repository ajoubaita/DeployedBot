"""Polymarket public market data clients (Gamma discovery and CLOB REST/WS).

This package provides read-only market discovery and market data access.
It intentionally avoids any trading/auth endpoints or flows.
"""

# runtime guardrails
from .guardrails import enforce as _enforce_guardrails
_enforce_guardrails()

from .gamma_client import GammaClient
from .clob_client import ClobClient
from .clob_ws_market import ClobWSMarket

__all__ = ["GammaClient", "ClobClient", "ClobWSMarket"]

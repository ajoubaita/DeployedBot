"""Client for Polymarket CLOB API (read-only).

Note: This client is read-only for market data. It does not support trading.
"""
import logging
import requests


class ClobClient:
    """Read-only client for Polymarket CLOB API.
    
    This client currently supports:
    - Getting active markets and their details
    - Getting orderbook snapshots
    - Getting market prices
    """

    def __init__(
        self,
        base_url: str = "https://clob.polymarket.com",
        timeout: int = 10,
        verify_ssl: bool = True,
        proxy: dict = None
    ):
        """Initialize CLOB client.
        
        Args:
            base_url: CLOB API base URL (default: https://clob.polymarket.com)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certs
            proxy: Optional proxy configuration for requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.proxy = proxy or {}

        # Configure session
        self.session = requests.Session()
        if proxy:
            self.session.proxies.update(proxy)

        # Configure logging
        self.log = logging.getLogger(__name__)

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Send GET request to CLOB API.
        
        Args:
            endpoint: API endpoint (e.g. "/order-book/snapshot")
            params: Optional query parameters
            
        Returns:
            API response as dict
            
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            resp = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            resp.raise_for_status()
            return resp.json()
            
        except requests.exceptions.RequestException as e:
            self.log.error(f"CLOB API error: {e}")
            raise

    def get_market_prices(self, token_ids: list) -> dict:
        """Get latest prices for specific market tokens.
        
        Args:
            token_ids: List of token IDs to get prices for
            
        Returns:
            Dict mapping token IDs to their current prices
        """
        resp = self._get("/prices", params={'tokenIds[]': token_ids})
        return resp.get('data', {})

    def get_orderbook_snapshot(self, token_id: str) -> dict:
        """Get orderbook snapshot for a market token.
        
        Args:
            token_id: Token ID to get orderbook for
            
        Returns:
            Dict containing orderbook bids and asks
        """
        return self._get(f"/order-book/snapshot/{token_id}")

    def get_simplified_markets(self) -> list:
        """Get simplified data for all active markets.
        
        This endpoint returns a list of active markets with their:
        - condition_id (matches Gamma API)
        - market status (active, accepting orders)
        - token ids and current prices
        - question/title

        Returns:
            List of market data dicts
        """
        return self._get("/markets-simplified")['data']
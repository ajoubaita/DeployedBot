"""CLOB WebSocket market streamer (read-only public channel).

Connects to the configured CLOB WS URL and subscribes to market updates.
Enforces that only the public 'market' channel is used.
"""
from typing import Iterable, List, Callable, Dict, Any, Optional
import os
import json
import threading
import time
import sys

try:
    import websocket
except Exception:
    websocket = None  # tests/usage will check and skip if not available

forbidden_channels = ('user',)

CLOB_WS_URL = os.environ.get('CLOB_WS_URL', 'wss://ws-subscriptions-clob.polymarket.com/ws/')


class ClobWSMarket:
    """Simple WS client that subscribes to market updates and yields parsed events.

    Usage:
        ws = ClobWSMarket()
        ws.connect()
        ws.subscribe_market(token_ids=[...])
        for ev in ws.stream(timeout=60):
            handle(ev)
    """

    def __init__(self, url: Optional[str] = None):
        self.url = url or CLOB_WS_URL
        self.ws = None
        self._recv_queue: List[Dict[str, Any]] = []
        self._stop = False

    def connect(self):
        if websocket is None:
            raise RuntimeError('websocket-client package is required for WS streaming')
        self.ws = websocket.WebSocketApp(self.url,
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close)
        self._thr = threading.Thread(target=self.ws.run_forever, daemon=True)
        self._thr.start()
        # wait briefly
        time.sleep(0.2)

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except Exception:
            return
        # guard: reject any messages about forbidden channels
        ch = data.get('channel') or data.get('topic') or ''
        if any(fc in ch for fc in forbidden_channels):
            raise RuntimeError(f'Forbidden channel in WS stream: {ch}')
        self._recv_queue.append(data)

    def _on_error(self, ws, err):
        print('WS error', err, file=sys.stderr)

    def _on_close(self, ws, code, reason):
        print('WS closed', code, reason, file=sys.stderr)

    def subscribe_market(self, token_ids: List[str]):
        if self.ws is None:
            raise RuntimeError('Not connected')
        # channel must be market
        msg = {'action': 'subscribe', 'channel': 'market', 'token_ids': token_ids}
        self.ws.send(json.dumps(msg))

    def stream(self, timeout: int = 60) -> Iterable[Dict[str, Any]]:
        """Yield messages received on the market channel within timeout seconds."""
        start = time.time()
        while time.time() - start < timeout:
            while self._recv_queue:
                yield self._recv_queue.pop(0)
            time.sleep(0.05)

    def close(self):
        self._stop = True
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

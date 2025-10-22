"""Simple demo to pull public market data from Polymarket (Gamma + CLOB).

This script is intentionally read-only and uses only public endpoints.
It prints a small summary of results and handles missing dependencies/endpoints gracefully.
"""
import os
import time
from polymarket import GammaClient, ClobClient


def main():
    print('Demo: Polymarket public market data')

    gamma_base = os.environ.get('GAMMA_API_BASE')
    clob_base = os.environ.get('CLOB_HTTP_BASE')

    print('GAMMA_API_BASE=', gamma_base)
    print('CLOB_HTTP_BASE=', clob_base)

    # Gamma discovery
    try:
        g = GammaClient()
        markets = g.get_markets()
        print(f'Fetched {len(markets)} markets (showing up to 10)')
        for m in markets[:10]:
            print('-', m.get('id'), m.get('slug'), 'end_time=', m.get('end_time'))
    except Exception as e:
        print('Gamma discovery failed:', e)

    # CLOB REST prices/books
    try:
        c = ClobClient()
        # collect up to 5 token ids from markets if present
        token_ids = [str(m.get('id')) for m in (markets or []) if m.get('id')][:5]
        if not token_ids:
            print('No token ids discovered to query prices for; trying example ids [1,2,3,4,5]')
            token_ids = ['1','2','3','4','5']

        reqs = []
        for tid in token_ids:
            reqs.append({'token_id': tid, 'side': 'BUY'})
            reqs.append({'token_id': tid, 'side': 'SELL'})

        print('Requesting batch prices for', len(reqs), 'items...')
        prices = c.get_prices(reqs)
        print('Prices response type:', type(prices))
        # print a few
        if isinstance(prices, list):
            for p in prices[:10]:
                print('  ', p)
        else:
            print('  ', prices)

        # request books for first two token ids
        for tid in token_ids[:2]:
            print('Requesting book for token', tid)
            book = c.get_book(tid)
            print('  book keys:', list(book.keys()) if isinstance(book, dict) else type(book))
    except Exception as e:
        print('CLOB REST queries failed:', e)

    # Optional: try WS streaming if websocket-client available and CLOB_WS_URL set
    try:
        from polymarket.clob_ws_market import ClobWSMarket
        ws_url = os.environ.get('CLOB_WS_URL')
        if ws_url:
            print('Attempting WS connect to', ws_url)
            ws = ClobWSMarket()
            try:
                ws.connect()
                # subscribe to a couple of token ids
                ws.subscribe_market(token_ids[:2] or ['1','2'])
                print('Streaming for 10s to capture messages...')
                for ev in ws.stream(timeout=10):
                    print('WS event:', ev)
                    break
            finally:
                ws.close()
        else:
            print('CLOB_WS_URL not set; skipping WS demo')
    except Exception as e:
        print('WS demo skipped:', e)


if __name__ == '__main__':
    main()

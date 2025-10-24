"""Demo script to pull live Polymarket data focusing on active markets.

This script:
1. Fetches and filters for active markets
2. Shows detailed market information
3. Attempts to get prices and books for recent market IDs
"""
import os
import time
from datetime import datetime
from polymarket import GammaClient, ClobClient

def main():
    print('Demo: Polymarket Live Market Data')
    print('=' * 50)

    gamma_base = os.environ.get('GAMMA_API_BASE')
    clob_base = os.environ.get('CLOB_HTTP_BASE')

    print('API Bases:')
    print('GAMMA_API_BASE =', gamma_base or '[default]')
    print('CLOB_HTTP_BASE =', clob_base or '[default]')
    print('=' * 50)

    # Gamma discovery
    try:
        g = GammaClient()
        print('\nFetching all markets...')
        all_markets = g.get_markets()
        print(f'Got {len(all_markets)} total markets')
        
        print('\nFiltering for active markets...')
        markets = g.filter_markets(active_only=True)
        print(f'Found {len(markets)} active markets')
        
        print('\nSample of markets (up to 5):')
        for m in markets[:5]:
            print('\nMARKET:')
            print('- ID:', m.get('id'))
            print('- Slug:', m.get('slug'))
            print('- End Time:', m.get('end_time'))
            if m.get('raw'):
                print('- Raw data keys:', list(m['raw'].keys()))

        # CLOB REST prices/books
        c = ClobClient()
        
        # Get token IDs to test with
        token_ids = [str(m.get('id')) for m in markets if m.get('id')]
        if not token_ids:
            print('\nNo active market IDs found; using test IDs [1-10]')
            token_ids = [str(i) for i in range(1, 11)]
        else:
            print(f'\nFound {len(token_ids)} active market token IDs')
            # Use a mix of IDs from different ranges
            test_ids = []
            test_ids.extend(token_ids[:3])  # First 3
            if len(token_ids) > 100:
                test_ids.extend(token_ids[98:100])  # Two from ~100
            if len(token_ids) > 1000:
                test_ids.extend(token_ids[998:1000])  # Two from ~1000
            token_ids = test_ids

        # Test batch price requests
        print('\nTesting batch price quotes...')
        reqs = []
        for tid in token_ids:
            reqs.append({'token_id': tid, 'side': 'BUY'})
            reqs.append({'token_id': tid, 'side': 'SELL'})

        print(f'Requesting prices for {len(token_ids)} markets ({len(reqs)} quotes)...')
        prices = c.get_prices(reqs)
        if isinstance(prices, dict):
            print('Price response keys:', list(prices.keys()))
            if prices:
                print('Sample price data:', next(iter(prices.items())))
        else:
            print('Unexpected price response type:', type(prices))

        # Test order books
        print('\nTesting order books...')
        for tid in token_ids:
            print(f'\nRequesting book for token {tid}')
            try:
                book = c.get_book(tid)
                if isinstance(book, dict):
                    print('- Response keys:', list(book.keys()))
                    if 'bids' in book:
                        print('- Bid levels:', len(book['bids']))
                        if book['bids']:
                            print('- Best bid:', book['bids'][0])
                    if 'asks' in book:
                        print('- Ask levels:', len(book['asks']))
                        if book['asks']:
                            print('- Best ask:', book['asks'][0])
                else:
                    print('- Unexpected response type:', type(book))
            except Exception as e:
                print('- Error:', str(e))

    except Exception as e:
        print('ERROR:', str(e))

if __name__ == '__main__':
    main()
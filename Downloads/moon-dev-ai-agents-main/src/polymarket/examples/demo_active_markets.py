"""Demo script to pull live Polymarket data focusing on active markets.

This script:
1. Fetches markets and filters for truly active ones
2. Shows detailed market information including prices
3. Uses proper CLOB token IDs from market data
"""
import os
import time
from datetime import datetime
from polymarket import GammaClient, ClobClient

def format_market(m):
    """Format key market details for display."""
    raw = m.get('raw', {})
    out = []
    out.append(f"ID: {m.get('id')}")
    out.append(f"Slug: {m.get('slug')}")
    out.append(f"End Time: {m.get('end_time')}")
    
    # Status flags
    flags = []
    if raw.get('active'):
        flags.append('active')
    if raw.get('closed'):
        flags.append('closed')
    if raw.get('ready'):
        flags.append('ready')
    if flags:
        out.append(f"Status: {', '.join(flags)}")
    
    # Market details
    if 'question' in raw:
        out.append(f"Question: {raw['question']}")
    if 'category' in raw:
        out.append(f"Category: {raw['category']}")
        
    # Trading details
    if 'lastTradePrice' in raw:
        out.append(f"Last Trade: {raw['lastTradePrice']}")
    if 'bestBid' in raw:
        out.append(f"Best Bid: {raw['bestBid']}")
    if 'bestAsk' in raw:
        out.append(f"Best Ask: {raw['bestAsk']}")
        
    # Volume/liquidity
    if 'volume24hr' in raw:
        out.append(f"24h Volume: {raw['volume24hr']}")
    if 'liquidity' in raw:
        out.append(f"Liquidity: {raw['liquidity']}")
        
    # CLOB details
    if 'clobTokenIds' in raw:
        out.append(f"CLOB Token IDs: {raw['clobTokenIds']}")
        
    # Outcomes
    if 'outcomes' in raw:
        out.append("Outcomes:")
        for i, o in enumerate(raw['outcomes']):
            price = raw.get('outcomePrices', [])[i] if i < len(raw.get('outcomePrices', [])) else None
            out.append(f"  {o}: {price if price is not None else 'N/A'}")
            
    return '\n'.join(f"- {line}" for line in out)

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
        
        # Filter for truly active markets
        now = datetime.utcnow().isoformat()
        markets = [
            m for m in all_markets 
            if m.get('raw', {}).get('active') 
            and not m.get('raw', {}).get('closed')
            and m.get('end_time', '9999') > now
        ]
        
        print(f'\nFound {len(markets)} truly active markets')
        print('\nSample of active markets (up to 3):')
        for m in markets[:3]:
            print('\nMARKET:')
            print(format_market(m))

        # CLOB REST prices/books
        c = ClobClient()
        
        # Collect CLOB token IDs from market data
        token_ids = []
        for m in markets[:5]:  # Try first 5 active markets
            clob_ids = m.get('raw', {}).get('clobTokenIds', [])
            if isinstance(clob_ids, list):
                token_ids.extend(str(tid) for tid in clob_ids)
            elif clob_ids:
                token_ids.append(str(clob_ids))
                
        if not token_ids:
            print('\nNo CLOB token IDs found in market data; using test range')
            token_ids = [str(i) for i in range(1000, 1010)]
        else:
            print(f'\nFound {len(token_ids)} CLOB token IDs in market data')
            if len(token_ids) > 6:
                print('Using first 6 token IDs for testing')
                token_ids = token_ids[:6]

        # Test batch price requests
        print('\nTesting batch price quotes...')
        reqs = []
        for tid in token_ids:
            reqs.append({'token_id': tid, 'side': 'BUY'})
            reqs.append({'token_id': tid, 'side': 'SELL'})

        print(f'Requesting prices for {len(token_ids)} markets ({len(reqs)} quotes)...')
        try:
            prices = c.get_prices(reqs)
            if isinstance(prices, dict):
                print('Price response keys:', list(prices.keys()))
                if prices:
                    print('Sample prices:')
                    for k, v in list(prices.items())[:3]:
                        print(f"- {k}: {v}")
            else:
                print('Unexpected price response type:', type(prices))
        except Exception as e:
            print('Price request failed:', str(e))

        # Test order books
        print('\nTesting order books...')
        for tid in token_ids[:3]:  # Test first 3 token IDs
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
"""Quick script to inspect CLOB market data structure."""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from polymarket import ClobClient

def main():
    clob = ClobClient()
    markets = clob.get_simplified_markets()
    
    # Check response structure
    print("\nResponse structure:")
    m = markets[0]
    print(json.dumps(m, indent=2))
    
    # Check some stats
    print("\nMarket stats:")
    print(f"Total markets: {len(markets)}")
    
    # Count markets with each field
    fields = ['condition_id', 'tokens', 'question', 'title', 'active']
    for field in fields:
        count = sum(1 for m in markets if m.get(field))
        print(f"Markets with {field}: {count}")
        
    # Sample of condition IDs
    print("\nSample condition IDs:")
    for m in markets[:3]:
        cond = m.get('condition_id', 'N/A')
        print(f"{cond}")

if __name__ == '__main__':
    main()
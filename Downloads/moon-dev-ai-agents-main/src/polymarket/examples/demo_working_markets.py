"""Working demo of Polymarket public API clients focusing on active markets.

This demo:
1. Gets active markets from Gamma API
2. Gets simplified market data from CLOB API 
3. Matches them by condition_id and shows current prices
"""
import os
import sys
from datetime import datetime
import textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from polymarket import GammaClient, ClobClient


def format_token_id(token_id: str) -> str:
    """Format token ID to ensure it's displayed as a full string."""
    try:
        # Convert scientific notation to full decimal string
        return format(int(token_id), 'd')
    except (ValueError, TypeError):
        return str(token_id)


def normalize_condition_id(cond_id: str) -> str:
    """Normalize condition ID format between APIs."""
    if not cond_id:
        return None
    
    # Always use the 0x prefix format since that's what CLOB uses
    cond_id = cond_id.lower()
    if not cond_id.startswith('0x'):
        cond_id = '0x' + cond_id
    return cond_id


def main():
    print("\n" + "="*70)
    print("  Polymarket Active Markets Demo")
    print("="*70)

    gamma = GammaClient()
    clob = ClobClient()

    # Step 1: Get active markets from Gamma
    print("\nStep 1: Discover active markets via Gamma API...")
    gamma_markets = gamma.filter_markets(active_only=True, open_only=True, limit=50)
    print(f"✓ Found {len(gamma_markets)} active markets from Gamma")

    print("\nSample of Gamma markets:")
    for i, m in enumerate(gamma_markets[:3], 1):
        print(f"\n{i}. {m.get('slug', 'Unknown')[:60]}")
        print(f"   ID: {m.get('id')}")
        cond_id = m.get('condition_id')
        print(f"   Condition ID: {cond_id}" if cond_id else "   Condition ID: N/A")
        print(f"   End Date: {m.get('end_time', 'N/A')}")
        print(f"   Volume: ${m.get('volume', 0):,.2f}" if m.get('volume') else "   Volume: N/A")

    # Step 2: Get all market prices from CLOB
    print("\nStep 2: Fetch current prices from CLOB API...")
    try:
        clob_markets = clob.get_simplified_markets()
        print(f"✓ Fetched {len(clob_markets)} markets from CLOB")

        print("\nSample of CLOB markets:")
        for i, m in enumerate(clob_markets[:3], 1):
            # Use first token outcome as title since CLOB doesn't have question/title
            tokens = m.get('tokens', [])
            title = tokens[0].get('outcome', 'Unknown') if tokens else 'Unknown Market'
            print(f"\n{i}. {title[:60]}")
            
            status = []
            if m.get('closed'):
                status.append('CLOSED')
            if m.get('archived'):
                status.append('ARCHIVED')
            if not status and m.get('active'):
                status.append('ACTIVE')
            status_str = ', '.join(status) if status else 'UNKNOWN'
            
            cond_id = m.get('condition_id', 'N/A')
            wrapped_cond = textwrap.fill(cond_id, width=50, subsequent_indent=' '*3)
            print(f"   Status: {status_str}")
            print(f"   Condition ID: {wrapped_cond}")
            print(f"   Accepting Orders: {m.get('accepting_orders', False)}")
            
            if tokens:
                print(f"   Outcomes ({len(tokens)}):")
                for t in tokens:
                    token_id = format_token_id(t.get('token_id', 'N/A'))
                    wrapped_token = textwrap.fill(token_id, width=50, subsequent_indent=' '*6)
                    price = t.get('price', 0)
                    winner = t.get('winner', False)
                    status = " [WINNER]" if winner else ""
                    print(f"     - {t.get('outcome', 'Unknown')}: ${price:.3f}{status}")
                    print(f"       Token ID: {wrapped_token}")

    except AttributeError:
        print("❌ Error: CLOB client doesn't have get_simplified_markets() method")
        print("   Please update the CLOB client to include this endpoint")
        return 1
    except Exception as e:
        print(f"❌ CLOB API error: {e}")
        return 1

    # Step 3: Match markets between Gamma and CLOB
    print("\nStep 3: Matching markets between Gamma and CLOB...")
    
    # Index CLOB markets by normalized condition ID (use 0x format)
    clob_by_condition = {}
    for m in clob_markets:
        if m.get('condition_id'):
            clob_by_condition[m['condition_id']] = m

    # Find matches - normalize Gamma condition IDs to match CLOB format
    matched = []
    for gm in gamma_markets:
        cond_id = normalize_condition_id(gm.get('condition_id'))
        if cond_id and cond_id in clob_by_condition:
            matched.append({
                'gamma': gm,
                'clob': clob_by_condition[cond_id]
            })

    print(f"✓ Matched {len(matched)} markets between APIs")

    # Show matched markets with full data
    print("\nMatched markets (showing up to 3):")
    for i, match in enumerate(matched[:3], 1):
        gm = match['gamma']
        cm = match['clob']
        
        # Use Gamma slug as primary title
        title = gm.get('slug', 'Unknown Market')
        print(f"\n{i}. {title[:60]}")
        
        # Market stats
        volume = gm.get('volume', 0)
        print(f"   Volume: ${volume:,.2f}" if volume else "   Volume: N/A")
        print(f"   End Date: {gm.get('end_time', 'N/A')}")
        
        # Market status
        status = []
        if cm.get('closed'):
            status.append('CLOSED')
        if cm.get('archived'):
            status.append('ARCHIVED')
        if not status and cm.get('active'):
            status.append('ACTIVE')
        status_str = ', '.join(status) if status else 'UNKNOWN'
        print(f"   Status: {status_str}")
        print(f"   Accepting Orders: {cm.get('accepting_orders', False)}")
        
        # Condition ID
        cond_id = cm.get('condition_id', 'N/A')
        wrapped_cond = textwrap.fill(cond_id, width=50, subsequent_indent=' '*3)
        print(f"   Condition ID: {wrapped_cond}")

        # Token details
        tokens = cm.get('tokens', [])
        if tokens:
            print(f"   Current Prices ({len(tokens)} outcomes):")
            for token in tokens:
                token_id = format_token_id(token.get('token_id', 'N/A'))
                wrapped_token = textwrap.fill(token_id, width=50, subsequent_indent=' '*6)
                outcome = token.get('outcome', 'Unknown')
                price = token.get('price', 0)
                winner = token.get('winner')
                status = " [WINNER]" if winner else ""
                print(f"     - {outcome}: ${price:.3f}{status}")
                print(f"       Token ID: {wrapped_token}")

    return 0


if __name__ == '__main__':
    exit(main())
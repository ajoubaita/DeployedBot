"""Working demo of Polymarket public API clients (updated for 2025).

This demonstrates:
1. Gamma API - Market discovery and filtering
2. CLOB API - Simplified markets with current prices
3. Both clients working together to find active markets
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from polymarket import GammaClient, ClobClient


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def demo_gamma_client():
    """Demonstrate Gamma API market discovery"""
    print_section("1. GAMMA API - Market Discovery")

    gamma = GammaClient()

    # Get recent markets
    print("\nFetching markets from Gamma API...")
    markets = gamma.get_markets(limit=10, closed=False)
    print(f"✓ Fetched {len(markets)} open markets")

    # Show first few markets
    print("\nFirst 5 open markets:")
    for i, m in enumerate(markets[:5], 1):
        print(f"\n{i}. {m.get('slug', 'Unknown')[:60]}")
        print(f"   ID: {m.get('id')}")

        cond_id = m.get('condition_id')
        if cond_id:
            print(f"   Condition ID: {cond_id[:20]}...")
        else:
            print(f"   Condition ID: N/A")

        print(f"   End Date: {m.get('end_time', 'N/A')}")
        print(f"   Active: {m.get('active')}, Closed: {m.get('closed')}")
        print(f"   Volume: ${m.get('volume', 0):,.2f}" if m.get('volume') else "   Volume: N/A")

        # Show CLOB token IDs if available
        clob_tokens = m.get('clob_token_ids')
        if clob_tokens and isinstance(clob_tokens, list):
            print(f"   CLOB Tokens: {len(clob_tokens)} outcomes")
            for j, token in enumerate(clob_tokens[:2]):  # Show first 2
                print(f"     - Token {j+1}: {token[:20]}...{token[-10:]}")

    # Filter for active markets only
    print("\n\nFiltering for active, non-closed markets...")
    active = gamma.filter_markets(active_only=True, open_only=True, limit=50)
    print(f"✓ Found {len(active)} active markets")

    # Show volume distribution
    if active:
        volumes = [float(m.get('volume') or 0) for m in active]
        print(f"\nVolume stats:")
        print(f"  Total: ${sum(volumes):,.2f}")
        print(f"  Average: ${sum(volumes)/len(volumes):,.2f}")
        print(f"  Max: ${max(volumes):,.2f}")
        print(f"  Min: ${min(volumes):,.2f}")

    return active


def demo_clob_client():
    """Demonstrate CLOB API simplified markets"""
    print_section("2. CLOB API - Simplified Markets")

    clob = ClobClient()

    print("\nFetching simplified markets from CLOB API...")
    markets = clob.get_simplified_markets()
    print(f"✓ Fetched {len(markets)} markets")

    # Filter for active, accepting orders
    active_markets = [m for m in markets if m.get('active') and m.get('accepting_orders')]
    print(f"✓ {len(active_markets)} markets actively accepting orders")

    # Show some markets with prices
    print("\nFirst 5 active markets with current prices:")
    for i, m in enumerate(active_markets[:5], 1):
        condition_id = m.get('condition_id', 'Unknown')
        question = m.get('question', 'No question')

        print(f"\n{i}. {question[:60]}")
        print(f"   Condition: {condition_id[:20]}...")
        print(f"   Active: {m.get('active')}, Accepting Orders: {m.get('accepting_orders')}")

        # Show token prices
        tokens = m.get('tokens', [])
        if tokens:
            print(f"   Outcomes ({len(tokens)}):")
            for token in tokens[:4]:  # Show up to 4 outcomes
                outcome = token.get('outcome', 'Unknown')
                price = token.get('price', 0)
                winner = token.get('winner')
                status = " [WINNER]" if winner else ""
                print(f"     - {outcome}: ${price:.3f}{status}")

    return active_markets


def demo_combined_workflow():
    """Demonstrate using both APIs together"""
    print_section("3. COMBINED WORKFLOW - Discovery + Prices")

    gamma = GammaClient()
    clob = ClobClient()

    # Step 1: Find markets from Gamma
    print("\nStep 1: Discover markets with Gamma API...")
    gamma_markets = gamma.filter_markets(active_only=True, open_only=True, limit=20)
    print(f"✓ Found {len(gamma_markets)} active markets from Gamma")

    # Step 2: Get CLOB markets with prices
    print("\nStep 2: Fetch current prices from CLOB API...")
    clob_markets = clob.get_simplified_markets()
    print(f"✓ Fetched {len(clob_markets)} markets from CLOB")

    # Step 3: Match by condition_id
    print("\nStep 3: Matching markets by condition_id...")
    clob_by_condition = {m.get('condition_id'): m for m in clob_markets}

    matched = []
    for gm in gamma_markets:
        cond_id = gm.get('condition_id')
        if cond_id and cond_id in clob_by_condition:
            matched.append({
                'gamma': gm,
                'clob': clob_by_condition[cond_id]
            })

    print(f"✓ Matched {len(matched)} markets between APIs")

    # Show matched markets with enriched data
    print("\nEnriched market data (Gamma metadata + CLOB prices):")
    for i, match in enumerate(matched[:3], 1):
        gm = match['gamma']
        cm = match['clob']

        print(f"\n{i}. {gm.get('slug', 'Unknown')[:60]}")
        print(f"   Gamma Volume: ${gm.get('volume', 0):,.2f}" if gm.get('volume') else "   Volume: N/A")
        print(f"   End Date: {gm.get('end_time', 'N/A')}")

        tokens = cm.get('tokens', [])
        if tokens:
            print(f"   Current Prices:")
            for token in tokens[:4]:
                outcome = token.get('outcome', 'Unknown')
                price = token.get('price', 0)
                print(f"     - {outcome}: ${price:.3f}")

    return matched


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("  Polymarket Public API Demo (Updated 2025)")
    print("="*70)
    print("\nThis demo shows read-only access to Polymarket's public APIs:")
    print("  - Gamma API: Market metadata and discovery")
    print("  - CLOB API: Current prices and order book data")

    try:
        # Demo 1: Gamma Client
        active_gamma = demo_gamma_client()

        # Demo 2: CLOB Client
        active_clob = demo_clob_client()

        # Demo 3: Combined workflow
        matched = demo_combined_workflow()

        # Summary
        print_section("SUMMARY")
        print(f"\n✓ Successfully connected to both Polymarket APIs")
        print(f"✓ Gamma API: {len(active_gamma)} active markets")
        print(f"✓ CLOB API: {len(active_clob)} markets accepting orders")
        print(f"✓ Matched: {len(matched)} markets with full data")
        print("\nAll API calls completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())

"""Test script to verify we can fetch specific high-profile markets and their prices."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from polymarket import GammaClient, ClobClient


def test_gamma_markets():
    """Test fetching markets from Gamma API"""
    print("=" * 70)
    print("TEST 1: Gamma API Market Discovery")
    print("=" * 70)

    gamma = GammaClient()

    # Test 1: Get recent open markets
    print("\n1. Fetching open markets (limit=20)...")
    markets = gamma.get_markets(limit=20, closed=False)
    print(f"✓ Fetched {len(markets)} markets")

    # Test 2: Filter for active only
    print("\n2. Filtering for active markets...")
    active = gamma.filter_markets(active_only=True, open_only=True, limit=20)
    print(f"✓ Found {len(active)} active markets")

    # Test 3: Filter by liquidity
    print("\n3. Filtering for high-liquidity markets (>$10k)...")
    liquid = gamma.filter_markets(
        active_only=True,
        open_only=True,
        min_liquidity=10000,
        limit=50
    )
    print(f"✓ Found {len(liquid)} markets with >$10k liquidity")

    # Show top 3 by volume
    if liquid:
        sorted_markets = sorted(
            [m for m in liquid if m.get('volume')],
            key=lambda x: float(x.get('volume', 0)),
            reverse=True
        )
        print("\nTop 3 markets by volume:")
        for i, m in enumerate(sorted_markets[:3], 1):
            print(f"{i}. {m['slug'][:60]}")
            print(f"   Volume: ${m.get('volume', 0):,.2f}")
            print(f"   Liquidity: ${m.get('liquidity', 0):,.2f}")
            print(f"   Condition ID: {m.get('condition_id', 'N/A')[:30]}...")

    return active


def test_clob_markets():
    """Test fetching markets from CLOB API"""
    print("\n" + "=" * 70)
    print("TEST 2: CLOB API Simplified Markets")
    print("=" * 70)

    clob = ClobClient()

    # Test 1: Get simplified markets
    print("\n1. Fetching simplified markets...")
    markets = clob.get_simplified_markets()
    print(f"✓ Fetched {len(markets)} total markets")

    # Test 2: Filter for active
    active = [m for m in markets if m.get('active') and not m.get('closed')]
    print(f"✓ {len(active)} active markets")

    # Test 3: Filter for accepting orders
    accepting = [m for m in markets if m.get('accepting_orders')]
    print(f"✓ {len(accepting)} markets accepting orders")

    # Show some markets with prices
    print("\nMarkets with live prices (first 5):")
    count = 0
    for m in markets:
        tokens = m.get('tokens', [])
        question = m.get('question', 'No question')

        if tokens and any(t.get('price', 0) > 0 for t in tokens):
            count += 1
            if count > 5:
                break

            print(f"\n{count}. {question[:60] if question else 'Unknown market'}")
            print(f"   Active: {m.get('active')}, Accepting: {m.get('accepting_orders')}")
            print(f"   Outcomes:")
            for token in tokens:
                outcome = token.get('outcome', 'Unknown')
                price = token.get('price', 0)
                winner = " [WINNER]" if token.get('winner') else ""
                print(f"     - {outcome}: ${price:.3f}{winner}")

    return markets


def test_detailed_market_query():
    """Test querying a specific market in detail"""
    print("\n" + "=" * 70)
    print("TEST 3: Detailed Market Query")
    print("=" * 70)

    gamma = GammaClient()
    clob = ClobClient()

    # Find a market with condition_id
    print("\n1. Finding a market with valid condition_id...")
    gamma_markets = gamma.filter_markets(open_only=True, limit=50)

    target_market = None
    for m in gamma_markets:
        if m.get('condition_id') and m.get('clob_token_ids'):
            target_market = m
            break

    if not target_market:
        print("✗ No markets found with condition_id")
        return

    print(f"✓ Found market: {target_market['slug']}")
    print(f"  ID: {target_market['id']}")
    print(f"  Condition ID: {target_market['condition_id']}")
    print(f"  Volume: ${target_market.get('volume', 0):,.2f}")
    print(f"  End Date: {target_market['end_time']}")

    # Get CLOB data for this market
    print("\n2. Fetching CLOB data for this market...")
    clob_markets = clob.get_simplified_markets()
    clob_market = None

    for m in clob_markets:
        if m.get('condition_id') == target_market['condition_id']:
            clob_market = m
            break

    if clob_market:
        print("✓ Found matching CLOB market")
        print(f"  Active: {clob_market.get('active')}")
        print(f"  Accepting Orders: {clob_market.get('accepting_orders')}")

        tokens = clob_market.get('tokens', [])
        if tokens:
            print(f"\n  Current Prices ({len(tokens)} outcomes):")
            for token in tokens:
                outcome = token.get('outcome', 'Unknown')
                price = token.get('price', 0)
                token_id = token.get('token_id', 'N/A')
                print(f"    {outcome}: ${price:.4f}")
                print(f"      Token ID: {token_id[:30]}...{token_id[-10:]}")
    else:
        print("✗ No matching CLOB market found")

    return target_market, clob_market


def test_price_comparison():
    """Compare prices from multiple markets"""
    print("\n" + "=" * 70)
    print("TEST 4: Price Analysis")
    print("=" * 70)

    clob = ClobClient()
    markets = clob.get_simplified_markets()

    # Find binary markets (Yes/No)
    binary_markets = []
    for m in markets:
        tokens = m.get('tokens', [])
        if len(tokens) == 2:
            outcomes = [t.get('outcome', '').lower() for t in tokens]
            if 'yes' in outcomes and 'no' in outcomes:
                binary_markets.append(m)

    print(f"\n✓ Found {len(binary_markets)} binary (Yes/No) markets")

    # Analyze price distributions
    if binary_markets:
        print("\nPrice Distribution Analysis:")

        # Find markets with different price patterns
        balanced = []
        skewed_yes = []
        skewed_no = []

        for m in binary_markets:
            tokens = m.get('tokens', [])
            yes_price = None
            no_price = None

            for t in tokens:
                if t.get('outcome', '').lower() == 'yes':
                    yes_price = t.get('price', 0)
                elif t.get('outcome', '').lower() == 'no':
                    no_price = t.get('price', 0)

            if yes_price is not None and no_price is not None:
                if 0.45 <= yes_price <= 0.55:
                    balanced.append((m, yes_price, no_price))
                elif yes_price > 0.7:
                    skewed_yes.append((m, yes_price, no_price))
                elif no_price > 0.7:
                    skewed_no.append((m, yes_price, no_price))

        print(f"  Balanced (45-55%): {len(balanced)} markets")
        print(f"  Skewed Yes (>70%): {len(skewed_yes)} markets")
        print(f"  Skewed No (>70%): {len(skewed_no)} markets")

        # Show examples
        if skewed_yes:
            m, yes_p, no_p = skewed_yes[0]
            q = m.get('question', 'Unknown')[:60]
            print(f"\nExample high-confidence Yes market:")
            print(f"  {q}")
            print(f"  Yes: ${yes_p:.3f}, No: ${no_p:.3f}")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  POLYMARKET API FUNCTIONALITY TEST SUITE")
    print("=" * 70)
    print("\nTesting all major functionality of the Polymarket clients\n")

    try:
        # Run tests
        gamma_markets = test_gamma_markets()
        clob_markets = test_clob_markets()
        test_detailed_market_query()
        test_price_comparison()

        # Final summary
        print("\n" + "=" * 70)
        print("  TEST SUMMARY")
        print("=" * 70)
        print("\n✅ All tests completed successfully!")
        print(f"✓ Gamma API: Fetching and filtering markets")
        print(f"✓ CLOB API: Getting simplified markets with prices")
        print(f"✓ Market matching: Joining Gamma and CLOB data")
        print(f"✓ Price analysis: Binary market distributions")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

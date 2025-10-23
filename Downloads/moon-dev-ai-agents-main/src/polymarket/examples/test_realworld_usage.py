"""Real-world usage examples for Polymarket API clients.

This demonstrates practical scenarios:
1. Finding high-volume trading opportunities
2. Monitoring market sentiment
3. Tracking market movements
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from polymarket import GammaClient, ClobClient
from datetime import datetime, timedelta


def find_trading_opportunities():
    """Find markets with high volume and liquidity for trading."""
    print("=" * 70)
    print("USE CASE 1: Finding Trading Opportunities")
    print("=" * 70)

    gamma = GammaClient()

    # Criteria: Active, open, high volume, good liquidity
    print("\nSearching for markets with:")
    print("  - Active (end date in future)")
    print("  - Open (not closed)")
    print("  - Volume > $100,000")
    print("  - Liquidity > $10,000")

    markets = gamma.filter_markets(
        active_only=True,
        open_only=True,
        min_liquidity=10000,
        limit=100
    )

    # Filter by volume
    high_volume = [m for m in markets if m.get('volume', 0) > 100000]

    print(f"\n✓ Found {len(high_volume)} high-volume markets")

    if high_volume:
        # Sort by volume
        sorted_markets = sorted(
            high_volume,
            key=lambda x: float(x.get('volume', 0)),
            reverse=True
        )

        print("\nTop 5 trading opportunities:")
        for i, m in enumerate(sorted_markets[:5], 1):
            slug = m.get('slug', 'Unknown')
            volume = m.get('volume', 0)
            liquidity = m.get('liquidity', 0)
            end_time = m.get('end_time', 'Unknown')

            # Calculate days until expiration
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                days_left = (end_dt - datetime.now(end_dt.tzinfo)).days
                days_str = f"{days_left} days"
            except:
                days_str = "Unknown"

            print(f"\n{i}. {slug[:60]}")
            print(f"   Volume: ${volume:,.2f}")
            print(f"   Liquidity: ${liquidity:,.2f}")
            print(f"   Expires in: {days_str}")
            print(f"   Condition ID: {m.get('condition_id', 'N/A')[:40]}...")

    return high_volume


def monitor_election_markets():
    """Monitor election-related prediction markets."""
    print("\n" + "=" * 70)
    print("USE CASE 2: Monitoring Election Markets")
    print("=" * 70)

    gamma = GammaClient()

    # Search for election markets
    print("\nSearching for election-related markets...")

    election_keywords = ['election', 'president', 'senate', 'congress', 'vote']
    all_markets = gamma.get_markets(limit=200, closed=False)

    election_markets = []
    for m in all_markets:
        slug = m.get('slug', '').lower()
        if any(keyword in slug for keyword in election_keywords):
            election_markets.append(m)

    print(f"✓ Found {len(election_markets)} election-related markets")

    if election_markets:
        # Filter for active with volume
        active_elections = [
            m for m in election_markets
            if m.get('active') and not m.get('closed') and m.get('volume', 0) > 0
        ]

        print(f"✓ {len(active_elections)} active markets with trading volume")

        # Sort by volume
        sorted_elections = sorted(
            active_elections,
            key=lambda x: float(x.get('volume', 0)),
            reverse=True
        )

        print("\nTop election markets by volume:")
        for i, m in enumerate(sorted_elections[:5], 1):
            print(f"\n{i}. {m.get('slug', 'Unknown')[:60]}")
            print(f"   Volume: ${m.get('volume', 0):,.2f}")
            print(f"   End Date: {m.get('end_time', 'Unknown')}")

    return election_markets


def analyze_market_sentiment():
    """Analyze overall market sentiment from price distributions."""
    print("\n" + "=" * 70)
    print("USE CASE 3: Market Sentiment Analysis")
    print("=" * 70)

    clob = ClobClient()

    print("\nFetching all markets with prices...")
    markets = clob.get_simplified_markets()

    # Analyze binary markets
    binary_markets = []
    for m in markets:
        tokens = m.get('tokens', [])
        if len(tokens) == 2:
            binary_markets.append(m)

    print(f"✓ Found {len(binary_markets)} binary outcome markets")

    # Calculate sentiment metrics
    total_yes = 0
    total_no = 0
    balanced_count = 0
    high_confidence_yes = 0
    high_confidence_no = 0

    for m in binary_markets:
        tokens = m.get('tokens', [])

        yes_price = None
        no_price = None

        for t in tokens:
            outcome = t.get('outcome', '').lower()
            price = t.get('price', 0)

            if 'yes' in outcome or 'win' in outcome:
                yes_price = price
            elif 'no' in outcome or 'lose' in outcome:
                no_price = price

        if yes_price is not None and no_price is not None:
            total_yes += yes_price
            total_no += no_price

            # Categorize
            if 0.4 <= yes_price <= 0.6:
                balanced_count += 1
            elif yes_price > 0.8:
                high_confidence_yes += 1
            elif no_price > 0.8:
                high_confidence_no += 1

    if binary_markets:
        print("\nMarket Sentiment Analysis:")
        print(f"  Average Yes Price: {total_yes / len(binary_markets):.3f}")
        print(f"  Average No Price: {total_no / len(binary_markets):.3f}")
        print(f"\nPrice Distribution:")
        print(f"  Balanced (40-60%): {balanced_count} markets ({balanced_count/len(binary_markets)*100:.1f}%)")
        print(f"  High Confidence Yes (>80%): {high_confidence_yes} markets ({high_confidence_yes/len(binary_markets)*100:.1f}%)")
        print(f"  High Confidence No (>80%): {high_confidence_no} markets ({high_confidence_no/len(binary_markets)*100:.1f}%)")


def track_expiring_markets():
    """Find markets expiring soon."""
    print("\n" + "=" * 70)
    print("USE CASE 4: Tracking Expiring Markets")
    print("=" * 70)

    gamma = GammaClient()

    print("\nSearching for markets expiring within 7 days...")

    markets = gamma.get_markets(limit=100, closed=False)

    now = datetime.utcnow()
    week_from_now = now + timedelta(days=7)

    expiring_soon = []
    for m in markets:
        end_time = m.get('end_time')
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                # Remove timezone for comparison
                end_dt_naive = end_dt.replace(tzinfo=None)

                if now <= end_dt_naive <= week_from_now:
                    days_left = (end_dt_naive - now).days
                    hours_left = (end_dt_naive - now).seconds // 3600
                    m['days_left'] = days_left
                    m['hours_left'] = hours_left
                    expiring_soon.append(m)
            except:
                pass

    print(f"✓ Found {len(expiring_soon)} markets expiring within 7 days")

    if expiring_soon:
        # Sort by expiration date
        sorted_expiring = sorted(
            expiring_soon,
            key=lambda x: x.get('days_left', 999) * 24 + x.get('hours_left', 0)
        )

        print("\nMarkets expiring soon:")
        for i, m in enumerate(sorted_expiring[:10], 1):
            days = m.get('days_left', 0)
            hours = m.get('hours_left', 0)
            print(f"\n{i}. {m.get('slug', 'Unknown')[:60]}")
            print(f"   Expires in: {days}d {hours}h")
            print(f"   Volume: ${m.get('volume', 0):,.2f}")
            print(f"   Active: {m.get('active')}")

    return expiring_soon


def main():
    """Run all real-world usage examples."""
    print("\n" + "=" * 70)
    print("  POLYMARKET REAL-WORLD USAGE EXAMPLES")
    print("=" * 70)
    print("\nDemonstrating practical applications of the API clients\n")

    try:
        # Run examples
        trading_opps = find_trading_opportunities()
        election_markets = monitor_election_markets()
        analyze_market_sentiment()
        expiring = track_expiring_markets()

        # Summary
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print("\n✅ All real-world use cases demonstrated successfully!")
        print(f"\n✓ Trading Opportunities: {len(trading_opps)} high-volume markets found")
        print(f"✓ Election Monitoring: {len(election_markets)} election markets tracked")
        print(f"✓ Sentiment Analysis: Price distributions calculated")
        print(f"✓ Expiring Markets: {len(expiring)} markets expiring within 7 days")

        print("\n" + "=" * 70)
        print("These examples show how to:")
        print("  1. Filter markets by volume and liquidity")
        print("  2. Search markets by topic/keyword")
        print("  3. Analyze price distributions and sentiment")
        print("  4. Track time-sensitive opportunities")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

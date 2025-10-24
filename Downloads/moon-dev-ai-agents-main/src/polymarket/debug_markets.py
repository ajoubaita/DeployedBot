"""Debug script to check market matching between Gamma and CLOB."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from polymarket.gamma_client import GammaClient
    from polymarket.clob_client import ClobClient
except ImportError:
    from gamma_client import GammaClient
    from clob_client import ClobClient


def main():
    print("Debugging market matching...\n")

    gamma = GammaClient()
    clob = ClobClient()

    # Get active markets from Gamma
    print("Fetching from Gamma API...")
    gamma_markets = gamma.filter_markets(
        active_only=True,
        open_only=True,
        min_liquidity=1000,
        limit=200
    )
    print(f"✓ Got {len(gamma_markets)} markets\n")

    # Filter by volume
    volume_filtered = [
        m for m in gamma_markets
        if 10000 <= m.get('volume', 0) <= 100000
        and m.get('condition_id')
    ]
    print(f"Markets in $10K-$100K range with condition_id: {len(volume_filtered)}")

    if volume_filtered:
        print("\nSample Gamma market:")
        sample = volume_filtered[0]
        print(f"  Slug: {sample.get('slug', 'N/A')}")
        print(f"  Condition ID: {sample.get('condition_id', 'N/A')}")
        print(f"  Volume: ${sample.get('volume', 0):,.2f}")
        print(f"  Liquidity: ${sample.get('liquidity', 0):,.2f}")

    # Get from CLOB
    print(f"\nFetching from CLOB API...")
    clob_markets = clob.get_simplified_markets()
    print(f"✓ Got {len(clob_markets)} markets")

    # Check condition_id format
    print(f"\nSample CLOB market:")
    if clob_markets:
        sample_clob = clob_markets[0]
        print(f"  Condition ID: {sample_clob.get('condition_id', 'N/A')}")
        print(f"  Question: {sample_clob.get('question', 'N/A')[:60]}")
        print(f"  Tokens: {len(sample_clob.get('tokens', []))}")

    # Build lookup
    clob_by_condition = {}
    for m in clob_markets:
        cid = m.get('condition_id')
        if cid:
            clob_by_condition[cid] = m

    print(f"\nCLOB markets with condition_id: {len(clob_by_condition)}")

    # Try to match
    matches = 0
    for gm in volume_filtered:
        cid = gm.get('condition_id')
        if cid in clob_by_condition:
            matches += 1

    print(f"Successful matches: {matches}/{len(volume_filtered)}")

    if matches == 0 and volume_filtered and clob_markets:
        print("\n❌ No matches found!")
        print("\nDEBUG INFO:")
        print(f"Sample Gamma condition_id: {volume_filtered[0].get('condition_id')}")
        print(f"Sample CLOB condition_id: {clob_markets[0].get('condition_id')}")
        print(f"Gamma condition_id type: {type(volume_filtered[0].get('condition_id'))}")
        print(f"CLOB condition_id type: {type(clob_markets[0].get('condition_id'))}")

        # Check if any Gamma IDs exist in CLOB
        gamma_ids = set(m.get('condition_id') for m in volume_filtered if m.get('condition_id'))
        clob_ids = set(m.get('condition_id') for m in clob_markets if m.get('condition_id'))

        print(f"\nGamma unique IDs: {len(gamma_ids)}")
        print(f"CLOB unique IDs: {len(clob_ids)}")
        print(f"Intersection: {len(gamma_ids & clob_ids)}")

        # Show some IDs
        print(f"\nFirst 5 Gamma IDs:")
        for cid in list(gamma_ids)[:5]:
            print(f"  {cid}")

        print(f"\nFirst 5 CLOB IDs:")
        for cid in list(clob_ids)[:5]:
            print(f"  {cid}")

    elif matches > 0:
        print(f"\n✓ Successfully matched {matches} markets")
        print("\nShowing first matched market:")
        for gm in volume_filtered:
            cid = gm.get('condition_id')
            if cid in clob_by_condition:
                cm = clob_by_condition[cid]
                print(f"\nGamma market:")
                print(f"  Slug: {gm.get('slug')}")
                print(f"  Volume: ${gm.get('volume'):,.2f}")
                print(f"  Condition ID: {cid}")

                print(f"\nCLOB market:")
                print(f"  Question: {cm.get('question', 'N/A')}")
                print(f"  Tokens: {len(cm.get('tokens', []))}")
                for token in cm.get('tokens', []):
                    print(f"    {token.get('outcome')}: ${token.get('price'):.3f}")
                break


if __name__ == '__main__':
    main()

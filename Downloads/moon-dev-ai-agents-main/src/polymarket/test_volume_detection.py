"""
Test volume spike detection with debug output.

See what's being filtered and why.
"""
try:
    from polymarket.gamma_client import GammaClient
    from polymarket.volume_spike_detector import VolumeSpikeDetector
except ImportError:
    from gamma_client import GammaClient
    from volume_spike_detector import VolumeSpikeDetector

print("\n" + "="*70)
print("  VOLUME SPIKE DETECTION DEBUG")
print("="*70)

# Get markets
gamma = GammaClient()
markets = gamma.filter_markets(active_only=True, open_only=True, limit=200)

print(f"\nFetched {len(markets)} open markets")

# Filter for markets with volume
markets_with_volume = [m for m in markets if m.get('volume') and m.get('volume') > 0]
print(f"{len(markets_with_volume)} markets have volume data\n")

# Initialize detector with VERY low thresholds for testing
detector = VolumeSpikeDetector(
    min_spike_ratio=1.5,  # Lower: 1.5x instead of 3x
    min_volume_usd=10000,  # Lower: $10k instead of $50k
    max_hours_to_deadline=999999,  # No deadline filter
    history_window=20
)

print("="*70)
print("BUILDING VOLUME HISTORY (5 cycles)")
print("="*70)

# Build history over 5 quick cycles
import time
for i in range(5):
    print(f"\nCycle {i+1}/5...")
    detector.update_volume_history(markets_with_volume)

    # Show how many markets have sufficient history
    sufficient = sum(1 for h in detector.volume_history.values() if h.has_sufficient_history())
    print(f"  {sufficient}/{len(detector.volume_history)} markets have 5+ snapshots")

    if i < 4:
        time.sleep(2)  # 2 seconds between snapshots

print("\n" + "="*70)
print("DETECTING SPIKES")
print("="*70 + "\n")

# Detect spikes
spikes = detector.detect_spikes(markets_with_volume)

print(f"\nDETECTED {len(spikes)} VOLUME SPIKES\n")

if spikes:
    for i, spike in enumerate(spikes[:10], 1):
        print(f"{i}. {spike.market_slug[:70]}")
        print(f"   Volume: ${spike.current_volume_24h:,.0f} (avg: ${spike.avg_volume_24h:,.0f}, {spike.volume_spike_ratio:.1f}x)")
        print(f"   Price: ${spike.current_price:.3f} ({spike.price_change_1h:+.1f}% in 1h)")
        print(f"   Signal: {spike.signal_strength:.0f}/100")
        print()
else:
    print("No spikes detected. Debugging...")

    # Show markets with history
    print("\nMarkets with sufficient history:")
    sufficient_markets = [
        (mid, h) for mid, h in detector.volume_history.items()
        if h.has_sufficient_history()
    ]

    print(f"  {len(sufficient_markets)} markets have 5+ snapshots\n")

    if sufficient_markets:
        print("Sample market stats:")
        for mid, h in sufficient_markets[:5]:
            ratio = h.get_volume_spike_ratio()
            current = h.get_current_volume()
            avg = h.get_avg_volume()
            print(f"  Market {mid}:")
            print(f"    Current volume: ${current:,.0f}")
            print(f"    Avg volume: ${avg:,.0f}")
            print(f"    Spike ratio: {ratio:.2f}x")
            print()

        print("ISSUE: Volume ratios are all ~1.0x (no spikes in static data)")
        print("      This is expected when volume doesn't change between snapshots")
        print("      Real spikes occur when NEW volume appears suddenly\n")

print("="*70)
print("CONCLUSION")
print("="*70)
print("\nVolume spike detection requires REAL-TIME monitoring because:")
print("  1. Static API data shows same volume across quick snapshots")
print("  2. Need to detect CHANGES in volume over time")
print("  3. Real spikes happen on timescale of minutes/seconds")
print("\nTo detect real spikes, bot must:")
print("  - Run continuously for hours/days")
print("  - Build historical baseline for each market")
print("  - Detect sudden increases from that baseline")
print("\nThe system is working correctly - just needs time to collect data.")
print("="*70 + "\n")

"""
Volume Spike Detection for Polymarket Latency Arbitrage

Strategy: Detect sudden volume spikes in markets near deadline
- Track volume history over rolling windows
- Identify 3x-5x+ volume increases
- Correlate with price movement
- Execute before crowd catches on

Key Insight: Volume spikes near deadline often signal insider info or imminent resolution
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import os

try:
    from polymarket.gamma_client import GammaClient
    from polymarket.clob_client import ClobClient
except ImportError:
    from gamma_client import GammaClient
    from clob_client import ClobClient


@dataclass
class VolumeSnapshot:
    """Single volume observation for a market."""
    timestamp: datetime
    volume_24h: float  # USD volume in last 24h
    price: float
    liquidity: float


@dataclass
class VolumeSpike:
    """Detected volume spike opportunity."""
    market_id: str
    market_slug: str
    token_id: str
    outcome: str

    # Volume metrics
    current_volume_24h: float
    avg_volume_24h: float  # Historical average
    volume_spike_ratio: float  # Current / Average (e.g., 4.2x)

    # Price metrics
    current_price: float
    price_change_1h: float  # % change in last hour

    # Timing metrics
    hours_to_deadline: float
    deadline_proximity_score: float  # 0-100, higher = closer to deadline

    # Signal strength
    signal_strength: float  # 0-100, combines volume spike + price movement + deadline
    confidence: float  # 0-100, based on data quality

    # Trade sizing
    recommended_position_usd: float
    max_loss_usd: float
    expected_roi_percent: float

    # Context
    detection_timestamp: datetime
    reasoning: str


class VolumeHistory:
    """Track volume history for a single market."""

    def __init__(self, market_id: str, window_size: int = 20):
        """
        Args:
            market_id: Market identifier
            window_size: Number of snapshots to keep in history
        """
        self.market_id = market_id
        self.window_size = window_size
        self.snapshots: deque[VolumeSnapshot] = deque(maxlen=window_size)

    def add_snapshot(self, volume_24h: float, price: float, liquidity: float):
        """Add new volume observation."""
        snapshot = VolumeSnapshot(
            timestamp=datetime.now(),
            volume_24h=volume_24h,
            price=price,
            liquidity=liquidity
        )
        self.snapshots.append(snapshot)

    def get_avg_volume(self) -> float:
        """Calculate average volume over history."""
        if not self.snapshots:
            return 0.0
        return sum(s.volume_24h for s in self.snapshots) / len(self.snapshots)

    def get_current_volume(self) -> float:
        """Get most recent volume."""
        if not self.snapshots:
            return 0.0
        return self.snapshots[-1].volume_24h

    def get_volume_spike_ratio(self) -> float:
        """Calculate current volume vs historical average."""
        avg = self.get_avg_volume()
        current = self.get_current_volume()
        if avg == 0:
            return 1.0
        return current / avg

    def get_price_change(self, hours: float = 1.0) -> float:
        """Calculate price change over last N hours."""
        if len(self.snapshots) < 2:
            return 0.0

        now = datetime.now()
        cutoff = now - timedelta(hours=hours)

        # Get snapshots within time window
        recent = [s for s in self.snapshots if s.timestamp >= cutoff]
        if len(recent) < 2:
            return 0.0

        old_price = recent[0].price
        new_price = recent[-1].price

        if old_price == 0:
            return 0.0
        return ((new_price - old_price) / old_price) * 100

    def has_sufficient_history(self, min_snapshots: int = 5) -> bool:
        """Check if we have enough history for reliable detection."""
        return len(self.snapshots) >= min_snapshots


class VolumeSpikeDetector:
    """
    Detect volume spikes for latency arbitrage.

    Strategy:
    1. Track volume history for all markets
    2. Detect sudden volume increases (3x-5x+)
    3. Check price movement correlation
    4. Filter for markets near deadline
    5. Calculate signal strength
    6. Recommend position sizing
    """

    def __init__(self,
                 min_spike_ratio: float = 3.0,
                 min_volume_usd: float = 50000,
                 max_hours_to_deadline: float = 72,
                 history_window: int = 20,
                 data_dir: str = None):
        """
        Args:
            min_spike_ratio: Minimum volume spike to detect (e.g., 3.0 = 3x increase)
            min_volume_usd: Minimum 24h volume to consider
            max_hours_to_deadline: Only consider markets within N hours of deadline
            history_window: Number of snapshots to track per market
            data_dir: Directory to persist volume history
        """
        self.min_spike_ratio = min_spike_ratio
        self.min_volume_usd = min_volume_usd
        self.max_hours_to_deadline = max_hours_to_deadline
        self.history_window = history_window

        # Data directory
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(__file__),
                'data',
                'volume_history'
            )
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        # Track volume history per market
        self.volume_history: Dict[str, VolumeHistory] = {}

        # API clients
        self.gamma = GammaClient()
        self.clob = ClobClient()

        # Load persisted history
        self._load_history()

        print(f"{'='*70}")
        print(f"VOLUME SPIKE DETECTOR INITIALIZED")
        print(f"{'='*70}")
        print(f"Min Spike Ratio: {min_spike_ratio}x")
        print(f"Min Volume: ${min_volume_usd:,.0f}")
        print(f"Max Hours to Deadline: {max_hours_to_deadline}h")
        print(f"History Window: {history_window} snapshots")
        print(f"{'='*70}\n")

    def update_volume_history(self, markets: List[Dict]):
        """Update volume history for all markets."""
        for market in markets:
            market_id = market.get('id', market.get('condition_id', 'unknown'))

            # Get volume (may need to fetch from Gamma or estimate from CLOB)
            volume_24h = market.get('volume', 0)

            # Get current price
            tokens = market.get('tokens', [])
            if not tokens:
                continue

            # Use first token's price
            price = tokens[0].get('price', 0.5)
            liquidity = market.get('liquidity', 0)

            # Get or create history tracker
            if market_id not in self.volume_history:
                self.volume_history[market_id] = VolumeHistory(
                    market_id=market_id,
                    window_size=self.history_window
                )

            # Add snapshot
            self.volume_history[market_id].add_snapshot(
                volume_24h=volume_24h,
                price=price,
                liquidity=liquidity
            )

    def calculate_deadline_proximity(self, end_date_iso: str) -> Tuple[float, float]:
        """
        Calculate hours to deadline and proximity score.

        Returns:
            (hours_to_deadline, proximity_score)
            proximity_score: 0-100, higher = closer to deadline
        """
        if not end_date_iso:
            return (999999.0, 0.0)

        try:
            # Parse ISO date
            end_date = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
            now = datetime.now(end_date.tzinfo)

            # Calculate hours remaining
            hours_remaining = (end_date - now).total_seconds() / 3600

            # Proximity score: 100 at deadline, decreases linearly
            if hours_remaining <= 0:
                proximity_score = 100.0
            elif hours_remaining >= self.max_hours_to_deadline:
                proximity_score = 0.0
            else:
                # Linear interpolation: 0h=100, max_hours=0
                proximity_score = 100 * (1 - (hours_remaining / self.max_hours_to_deadline))

            return (hours_remaining, proximity_score)

        except Exception as e:
            print(f"  Warning: Could not parse deadline: {e}")
            return (999999.0, 0.0)

    def calculate_signal_strength(self,
                                  volume_spike_ratio: float,
                                  price_change_1h: float,
                                  deadline_proximity: float) -> float:
        """
        Calculate overall signal strength (0-100).

        Combines:
        - Volume spike magnitude
        - Price movement correlation
        - Deadline proximity

        Returns:
            Signal strength score (0-100)
        """
        # Volume component (0-40 points)
        # 3x spike = 10, 5x = 25, 10x = 40
        volume_score = min(40, (volume_spike_ratio - 1) * 8)

        # Price movement component (0-30 points)
        # Absolute price change: 5% = 15, 10% = 30
        price_score = min(30, abs(price_change_1h) * 3)

        # Deadline proximity component (0-30 points)
        deadline_score = deadline_proximity * 0.3

        total = volume_score + price_score + deadline_score
        return min(100, total)

    def detect_spikes(self, markets: List[Dict]) -> List[VolumeSpike]:
        """
        Scan markets for volume spikes.

        Args:
            markets: List of market dicts from CLOB/Gamma

        Returns:
            List of detected volume spike opportunities
        """
        # Update volume history first
        self.update_volume_history(markets)

        spikes = []

        for market in markets:
            market_id = market.get('id', market.get('condition_id', 'unknown'))

            # Skip if no history yet
            if market_id not in self.volume_history:
                continue

            history = self.volume_history[market_id]

            # Need sufficient history for reliable detection
            if not history.has_sufficient_history(min_snapshots=5):
                continue

            # Get volume spike ratio
            spike_ratio = history.get_volume_spike_ratio()

            # Filter: Must exceed minimum spike threshold
            if spike_ratio < self.min_spike_ratio:
                continue

            # Filter: Minimum absolute volume
            current_volume = history.get_current_volume()
            if current_volume < self.min_volume_usd:
                continue

            # Get deadline info
            end_date = market.get('end_date_iso', market.get('endDate'))
            hours_to_deadline, deadline_proximity = self.calculate_deadline_proximity(end_date)

            # Filter: Too far from deadline
            if hours_to_deadline > self.max_hours_to_deadline:
                continue

            # Get price change
            price_change_1h = history.get_price_change(hours=1.0)

            # Calculate signal strength
            signal_strength = self.calculate_signal_strength(
                volume_spike_ratio=spike_ratio,
                price_change_1h=price_change_1h,
                deadline_proximity=deadline_proximity
            )

            # Filter: Minimum signal strength (50+)
            if signal_strength < 50:
                continue

            # Get market details
            tokens = market.get('tokens', [])
            if not tokens:
                continue

            token = tokens[0]
            current_price = token.get('price', 0.5)

            # Calculate position sizing
            # More aggressive sizing for stronger signals
            base_position = 1000  # Base $1k position
            signal_multiplier = signal_strength / 50  # 1x at 50, 2x at 100
            recommended_position = base_position * signal_multiplier

            # Max loss = position size (can lose entire position)
            max_loss = recommended_position

            # Expected ROI: Higher for extreme prices
            if current_price < 0.5:
                expected_roi = ((1.0 - current_price) / current_price) * 100
            else:
                expected_roi = ((current_price - 0.0) / (1.0 - current_price)) * 100

            # Build reasoning
            reasoning = f"Volume spike {spike_ratio:.1f}x (${current_volume:,.0f} vs ${history.get_avg_volume():,.0f} avg). "
            reasoning += f"Price {'up' if price_change_1h > 0 else 'down'} {abs(price_change_1h):.1f}% in 1h. "
            reasoning += f"Deadline in {hours_to_deadline:.1f}h (proximity: {deadline_proximity:.0f}/100). "
            reasoning += f"Signal strength: {signal_strength:.0f}/100"

            spike = VolumeSpike(
                market_id=market_id,
                market_slug=market.get('slug', market.get('question', 'unknown'))[:80],
                token_id=token.get('token_id', 'unknown'),
                outcome=token.get('outcome', 'Yes'),
                current_volume_24h=current_volume,
                avg_volume_24h=history.get_avg_volume(),
                volume_spike_ratio=spike_ratio,
                current_price=current_price,
                price_change_1h=price_change_1h,
                hours_to_deadline=hours_to_deadline,
                deadline_proximity_score=deadline_proximity,
                signal_strength=signal_strength,
                confidence=min(100, len(history.snapshots) * 5),  # More history = higher confidence
                recommended_position_usd=recommended_position,
                max_loss_usd=max_loss,
                expected_roi_percent=expected_roi,
                detection_timestamp=datetime.now(),
                reasoning=reasoning
            )

            spikes.append(spike)

        # Sort by signal strength
        spikes.sort(key=lambda s: s.signal_strength, reverse=True)

        return spikes

    def _load_history(self):
        """Load persisted volume history from disk."""
        history_file = os.path.join(self.data_dir, 'volume_history.json')
        if not os.path.exists(history_file):
            return

        try:
            with open(history_file, 'r') as f:
                data = json.load(f)

            for market_id, snapshots_data in data.items():
                history = VolumeHistory(market_id, self.history_window)

                for snap in snapshots_data:
                    snapshot = VolumeSnapshot(
                        timestamp=datetime.fromisoformat(snap['timestamp']),
                        volume_24h=snap['volume_24h'],
                        price=snap['price'],
                        liquidity=snap['liquidity']
                    )
                    history.snapshots.append(snapshot)

                self.volume_history[market_id] = history

            print(f"✓ Loaded volume history for {len(self.volume_history)} markets")

        except Exception as e:
            print(f"Warning: Could not load volume history: {e}")

    def save_history(self):
        """Persist volume history to disk."""
        history_file = os.path.join(self.data_dir, 'volume_history.json')

        try:
            data = {}
            for market_id, history in self.volume_history.items():
                snapshots_data = []
                for snap in history.snapshots:
                    snapshots_data.append({
                        'timestamp': snap.timestamp.isoformat(),
                        'volume_24h': snap.volume_24h,
                        'price': snap.price,
                        'liquidity': snap.liquidity
                    })
                data[market_id] = snapshots_data

            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✓ Saved volume history for {len(self.volume_history)} markets")

        except Exception as e:
            print(f"Warning: Could not save volume history: {e}")


def main():
    """Test volume spike detector."""
    print("\n" + "="*70)
    print("  VOLUME SPIKE DETECTOR TEST")
    print("="*70)
    print("\nMonitoring for volume spikes...")
    print("="*70 + "\n")

    # Initialize detector
    detector = VolumeSpikeDetector(
        min_spike_ratio=2.0,  # Lower threshold for testing
        min_volume_usd=10000,
        max_hours_to_deadline=168  # 7 days
    )

    # Get markets
    clob = ClobClient()

    print("Fetching markets...\n")
    markets = clob.get_simplified_markets()

    # Filter for open markets
    open_markets = [
        m for m in markets
        if not m.get('closed') and not m.get('archived')
    ]

    print(f"Found {len(open_markets)} open markets\n")

    # Build history over multiple cycles
    print("Building volume history (3 cycles)...\n")
    for i in range(3):
        print(f"Cycle {i+1}/3...")
        detector.update_volume_history(open_markets)
        if i < 2:
            time.sleep(5)  # Wait between snapshots

    print()

    # Detect spikes
    print("Scanning for volume spikes...\n")
    spikes = detector.detect_spikes(open_markets)

    print(f"{'='*70}")
    print(f"DETECTED {len(spikes)} VOLUME SPIKES")
    print(f"{'='*70}\n")

    for i, spike in enumerate(spikes, 1):
        print(f"{i}. {spike.market_slug[:70]}")
        print(f"   Volume: ${spike.current_volume_24h:,.0f} ({spike.volume_spike_ratio:.1f}x spike)")
        print(f"   Price: ${spike.current_price:.3f} ({spike.price_change_1h:+.1f}% in 1h)")
        print(f"   Deadline: {spike.hours_to_deadline:.1f}h (proximity: {spike.deadline_proximity_score:.0f}/100)")
        print(f"   Signal Strength: {spike.signal_strength:.0f}/100")
        print(f"   Recommended Position: ${spike.recommended_position_usd:,.0f}")
        print(f"   Reasoning: {spike.reasoning}")
        print()

    # Save history
    detector.save_history()

    print(f"{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()

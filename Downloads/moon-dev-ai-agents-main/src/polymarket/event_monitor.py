"""
Polymarket Event Monitor

Monitors real-time events and maps them to Polymarket markets for arbitrage detection.
Focuses on certainty-based events (sports scores, official announcements) with low latency.

Key Requirements:
- Event detection latency < 1 second
- Market volume filter: $10K-$100K
- Integration with arbitrage_detector for opportunity validation
- Integration with existing moon-dev agents for trade analysis
"""
import time
import json
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from threading import Thread, Lock

try:
    from polymarket.gamma_client import GammaClient
    from polymarket.clob_client import ClobClient
    from polymarket.arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity
except ImportError:
    # Running as script from polymarket directory
    from gamma_client import GammaClient
    from clob_client import ClobClient
    from arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity


@dataclass
class DetectedEvent:
    """Represents a detected real-world event."""
    event_id: str
    event_type: str  # 'sports', 'news', 'economic'
    description: str
    outcome: str  # 'Team A Won', 'Bill Passed', etc
    timestamp: datetime
    source: str  # 'ESPN API', 'Reuters', etc
    source_credibility: float  # 0-1
    is_reversible: bool  # Can outcome be reversed?
    metadata: Dict  # Additional context


@dataclass
class MarketMatch:
    """Maps a detected event to a Polymarket market."""
    event: DetectedEvent
    market: Dict
    confidence: float  # How confident is the match? 0-1
    matched_outcome: str  # Which market outcome matches the event
    match_reasoning: str


class EventSource:
    """Base class for event sources (ESPN, news feeds, etc)."""

    def __init__(self, source_name: str, credibility: float = 0.9):
        self.source_name = source_name
        self.credibility = credibility
        self.is_running = False

    def start(self):
        """Start monitoring this source."""
        self.is_running = True

    def stop(self):
        """Stop monitoring this source."""
        self.is_running = False

    def poll_events(self) -> List[DetectedEvent]:
        """Poll for new events. Override in subclass."""
        raise NotImplementedError


class MarketMatcher:
    """Matches detected events to Polymarket markets."""

    def __init__(self, gamma_client: GammaClient, clob_client: ClobClient):
        self.gamma = gamma_client
        self.clob = clob_client
        self.market_cache = []
        self.last_refresh = None
        self.cache_ttl_seconds = 300  # 5 minutes

    def refresh_market_cache(self, min_volume: float = 10000, max_volume: float = 100000):
        """
        Refresh the cache of active markets in target volume range.

        Args:
            min_volume: Minimum market volume in USD
            max_volume: Maximum market volume in USD
        """
        print(f"[MarketMatcher] Refreshing market cache (${min_volume:,} - ${max_volume:,} volume)...")

        # Get active markets from Gamma
        gamma_markets = self.gamma.filter_markets(
            active_only=True,
            open_only=True,
            min_liquidity=1000,
            limit=200
        )

        # Filter by volume range
        filtered = [
            m for m in gamma_markets
            if min_volume <= m.get('volume', 0) <= max_volume
            and m.get('condition_id')  # Must have condition_id for price matching
        ]

        # Get current prices from CLOB
        clob_markets = self.clob.get_simplified_markets()
        clob_by_condition = {m['condition_id']: m for m in clob_markets}

        # Combine metadata + prices
        combined = []
        for gm in filtered:
            cond_id = gm.get('condition_id')
            if cond_id in clob_by_condition:
                cm = clob_by_condition[cond_id]
                gm['tokens'] = cm.get('tokens', [])
                gm['accepting_orders'] = cm.get('accepting_orders', False)
                combined.append(gm)

        self.market_cache = combined
        self.last_refresh = datetime.now()

        print(f"[MarketMatcher] Cached {len(self.market_cache)} markets in target range")

    def should_refresh_cache(self) -> bool:
        """Check if cache needs refresh."""
        if not self.last_refresh:
            return True
        age = (datetime.now() - self.last_refresh).total_seconds()
        return age > self.cache_ttl_seconds

    def match_event_to_markets(self, event: DetectedEvent) -> List[MarketMatch]:
        """
        Find Polymarket markets that match this event.

        Args:
            event: The detected event

        Returns:
            List of potential market matches
        """
        if self.should_refresh_cache():
            self.refresh_market_cache()

        matches = []

        # Simple keyword matching for now (can be enhanced with AI)
        event_keywords = self._extract_keywords(event.description)

        for market in self.market_cache:
            market_text = f"{market.get('slug', '')} {market.get('question', '')}".lower()

            # Calculate match score
            matched_keywords = sum(1 for kw in event_keywords if kw in market_text)
            confidence = min(1.0, matched_keywords / max(len(event_keywords), 1))

            if confidence > 0.5:  # Threshold for consideration
                # Try to match event outcome to market token
                matched_outcome = self._match_outcome_to_token(
                    event.outcome,
                    market.get('tokens', [])
                )

                if matched_outcome:
                    matches.append(MarketMatch(
                        event=event,
                        market=market,
                        confidence=confidence,
                        matched_outcome=matched_outcome,
                        match_reasoning=f"Matched {matched_keywords}/{len(event_keywords)} keywords"
                    ))

        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text for matching."""
        # Simple implementation - remove common words
        stopwords = {'the', 'a', 'an', 'in', 'on', 'at', 'will', 'be', 'to', 'of'}
        words = text.lower().split()
        return [w for w in words if w not in stopwords and len(w) > 2]

    def _match_outcome_to_token(self, outcome: str, tokens: List[Dict]) -> Optional[str]:
        """Match event outcome to market token outcome."""
        outcome_lower = outcome.lower()

        for token in tokens:
            token_outcome = token.get('outcome', '').lower()

            # Direct match
            if outcome_lower in token_outcome or token_outcome in outcome_lower:
                return token.get('outcome')

            # Binary markets: look for positive indicators in outcome
            if 'yes' in token_outcome and any(word in outcome_lower for word in ['win', 'pass', 'yes', 'true', 'happen']):
                return token.get('outcome')
            if 'no' in token_outcome and any(word in outcome_lower for word in ['lose', 'fail', 'no', 'false', 'not']):
                return token.get('outcome')

        return None


class EventMonitor:
    """
    Main event monitoring system.

    Orchestrates multiple event sources, matches events to markets,
    and validates arbitrage opportunities.
    """

    def __init__(
        self,
        min_volume: float = 10000,
        max_volume: float = 100000,
        min_roi: float = 0.20
    ):
        self.gamma = GammaClient()
        self.clob = ClobClient()
        self.matcher = MarketMatcher(self.gamma, self.clob)
        self.detector = ArbitrageDetector()

        self.min_volume = min_volume
        self.max_volume = max_volume
        self.min_roi = min_roi

        self.event_sources: List[EventSource] = []
        self.detected_opportunities: List[ArbitrageOpportunity] = []

        self.is_running = False
        self._lock = Lock()

        # Callbacks for when opportunities are found
        self.opportunity_callbacks: List[Callable] = []

    def add_event_source(self, source: EventSource):
        """Add an event source to monitor."""
        self.event_sources.append(source)
        print(f"[EventMonitor] Added event source: {source.source_name}")

    def add_opportunity_callback(self, callback: Callable):
        """Add callback to be called when opportunity is detected."""
        self.opportunity_callbacks.append(callback)

    def start(self):
        """Start monitoring all event sources."""
        print("[EventMonitor] Starting event monitoring...")

        self.is_running = True

        # Start all event sources
        for source in self.event_sources:
            source.start()

        # Start monitoring loop
        monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()

        print(f"[EventMonitor] Monitoring {len(self.event_sources)} event sources")

    def stop(self):
        """Stop monitoring."""
        print("[EventMonitor] Stopping event monitoring...")
        self.is_running = False

        for source in self.event_sources:
            source.stop()

    def _monitoring_loop(self):
        """Main monitoring loop - runs in background thread."""
        while self.is_running:
            try:
                # Poll all event sources
                for source in self.event_sources:
                    if not source.is_running:
                        continue

                    events = source.poll_events()

                    for event in events:
                        self._process_event(event)

            except Exception as e:
                print(f"[EventMonitor] Error in monitoring loop: {e}")

            # Small delay to avoid CPU spinning
            time.sleep(0.1)

    def _process_event(self, event: DetectedEvent):
        """
        Process a detected event - match to markets and check for arbitrage.

        Args:
            event: The detected event
        """
        print(f"\n[EventMonitor] Processing event: {event.description}")
        print(f"  Outcome: {event.outcome}")
        print(f"  Source: {event.source} (credibility={event.source_credibility:.2f})")

        # Match event to markets
        matches = self.matcher.match_event_to_markets(event)

        print(f"  Found {len(matches)} potential market matches")

        for match in matches[:5]:  # Process top 5 matches
            print(f"\n  Checking match: {match.market.get('slug', 'Unknown')[:60]}")
            print(f"    Confidence: {match.confidence:.2f}")
            print(f"    Volume: ${match.market.get('volume', 0):,.2f}")

            # Validate arbitrage opportunity
            certainty_info = self._build_certainty_info(event)

            opportunity = self.detector.detect_opportunity(
                market=match.market,
                event_outcome=match.matched_outcome,
                event_timestamp=event.timestamp,
                certainty_info=certainty_info
            )

            if opportunity:
                print(f"    ✓ OPPORTUNITY DETECTED!")
                print(f"      ROI: {opportunity.roi_percent:.1f}%")
                print(f"      Net Profit: ${opportunity.net_profit:,.2f}")
                print(f"      Certainty: {opportunity.certainty_score * 100:.1f}%")

                with self._lock:
                    self.detected_opportunities.append(opportunity)

                # Trigger callbacks
                for callback in self.opportunity_callbacks:
                    try:
                        callback(opportunity)
                    except Exception as e:
                        print(f"    Error in opportunity callback: {e}")
            else:
                print(f"    ✗ No valid opportunity (ROI or certainty too low)")

    def _build_certainty_info(self, event: DetectedEvent) -> Dict:
        """Convert DetectedEvent to certainty_info dict for ArbitrageDetector."""
        if event.event_type == 'sports':
            return {
                'type': 'sports',
                'game_status': 'FINAL',  # Assume event is final
                'final_score': event.metadata.get('score'),
                'source': event.source
            }
        elif event.event_type == 'news':
            return {
                'type': 'news',
                'announcement_made': True,
                'source_credibility': event.source_credibility,
                'multiple_sources': event.metadata.get('multiple_sources', False),
                'reversible': event.is_reversible
            }
        else:
            return {
                'type': 'unknown'
            }

    def get_opportunities(self, min_roi: Optional[float] = None) -> List[ArbitrageOpportunity]:
        """
        Get all detected opportunities.

        Args:
            min_roi: Optional minimum ROI filter

        Returns:
            List of opportunities
        """
        with self._lock:
            if min_roi is None:
                min_roi = self.min_roi

            return [
                opp for opp in self.detected_opportunities
                if opp.roi_percent >= (min_roi * 100)
            ]


# Example event source implementation
class MockSportsEventSource(EventSource):
    """Mock sports event source for testing."""

    def __init__(self):
        super().__init__("Mock Sports API", credibility=1.0)
        self.events_to_emit = []

    def add_mock_event(self, description: str, outcome: str, metadata: Dict = None):
        """Add a mock event to emit on next poll."""
        event = DetectedEvent(
            event_id=f"mock_{int(time.time())}",
            event_type='sports',
            description=description,
            outcome=outcome,
            timestamp=datetime.now(),
            source=self.source_name,
            source_credibility=self.credibility,
            is_reversible=False,
            metadata=metadata or {}
        )
        self.events_to_emit.append(event)

    def poll_events(self) -> List[DetectedEvent]:
        """Return any pending mock events."""
        events = self.events_to_emit.copy()
        self.events_to_emit.clear()
        return events


# Example usage
if __name__ == "__main__":
    # Create monitor
    monitor = EventMonitor(
        min_volume=10000,
        max_volume=100000,
        min_roi=0.20
    )

    # Add callback for opportunities
    def opportunity_found(opp: ArbitrageOpportunity):
        print(f"\n{'='*70}")
        print(f"ARBITRAGE OPPORTUNITY CALLBACK")
        print(f"{'='*70}")
        print(f"Market: {opp.market_slug}")
        print(f"Outcome: {opp.outcome}")
        print(f"Position: ${opp.position_size_usd:,.2f}")
        print(f"Net Profit: ${opp.net_profit:,.2f}")
        print(f"ROI: {opp.roi_percent:.1f}%")
        print(f"Certainty: {opp.certainty_score * 100:.1f}%")
        print(f"{'='*70}\n")

    monitor.add_opportunity_callback(opportunity_found)

    # Add mock event source
    mock_source = MockSportsEventSource()
    monitor.add_event_source(mock_source)

    # Start monitoring
    monitor.start()

    print("\n" + "="*70)
    print("EVENT MONITOR RUNNING")
    print("="*70)
    print("Simulating event detection...")

    # Simulate event after 2 seconds
    time.sleep(2)

    mock_source.add_mock_event(
        description="Lakers vs Celtics NBA game final score",
        outcome="Lakers Won",
        metadata={'score': {'lakers': 108, 'celtics': 95}}
    )

    print("\n✓ Mock event added: Lakers won game")
    print("  Event monitor will process and match to markets...")

    # Let it run for 10 seconds
    time.sleep(10)

    # Get results
    opportunities = monitor.get_opportunities()

    print(f"\n\nFinal Results:")
    print(f"{'='*70}")
    print(f"Total opportunities detected: {len(opportunities)}")

    if opportunities:
        print("\nTop opportunities:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"\n{i}. {opp.market_slug[:60]}")
            print(f"   ROI: {opp.roi_percent:.1f}%")
            print(f"   Profit: ${opp.net_profit:,.2f}")
            print(f"   Certainty: {opp.certainty_score * 100:.1f}%")
    else:
        print("\nNo opportunities met the criteria")
        print("(This is expected with mock data if no matching markets exist)")

    # Stop
    monitor.stop()
    print("\n✓ Event monitor stopped")

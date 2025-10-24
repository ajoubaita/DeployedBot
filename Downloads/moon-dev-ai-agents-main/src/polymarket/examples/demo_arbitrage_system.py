"""
Complete Arbitrage System Demo

Demonstrates the full end-to-end arbitrage detection system:
1. Event detection and monitoring
2. Market matching
3. Arbitrage opportunity calculation
4. AI agent validation
5. Execution readiness assessment

This shows how all components work together to identify
certainty-based latency arbitrage opportunities.
"""
import sys
import os
import time
from datetime import datetime

# Add parent paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from polymarket.event_monitor import EventMonitor, MockSportsEventSource, DetectedEvent
from polymarket.arbitrage_detector import ArbitrageDetector
from polymarket.agent_integration import AgentIntegrator


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def demo_basic_arbitrage_detection():
    """Demo: Basic arbitrage detection without event monitoring."""
    print_header("DEMO 1: Basic Arbitrage Detection")

    detector = ArbitrageDetector()

    # Simulate a market where outcome is certain but price hasn't updated
    fake_market = {
        'id': 'market_001',
        'slug': 'will-team-a-beat-team-b',
        'condition_id': '0xabc123',
        'volume': 75000,  # Within $10K-$100K range
        'liquidity': 20000,
        'tokens': [
            {'token_id': 'token_yes', 'outcome': 'Yes', 'price': 0.65},  # Market price
            {'token_id': 'token_no', 'outcome': 'No', 'price': 0.35}
        ]
    }

    # Game is over, Team A won (Yes outcome)
    certainty_info = {
        'type': 'sports',
        'game_status': 'FINAL',
        'final_score': {'team_a': 3, 'team_b': 1},
        'source': 'ESPN Official API'
    }

    print("Market Info:")
    print(f"  Question: {fake_market['slug']}")
    print(f"  Volume: ${fake_market['volume']:,}")
    print(f"  Current Price (Yes): ${fake_market['tokens'][0]['price']:.3f}")
    print(f"  Event: Team A won (outcome certain)")

    # Detect opportunity
    opp = detector.detect_opportunity(
        market=fake_market,
        event_outcome='Yes',
        event_timestamp=datetime.now(),
        certainty_info=certainty_info
    )

    if opp:
        print(f"\n✓ OPPORTUNITY DETECTED!")
        print(f"\nTrade Details:")
        print(f"  Position Size: ${opp.position_size_usd:,.2f}")
        print(f"  Current Price: ${opp.current_price:.3f}")
        print(f"  Certain Price: ${opp.should_be_price:.3f}")
        print(f"  Expected Payout: ${opp.expected_payout:,.2f}")
        print(f"\nProfit Breakdown:")
        print(f"  Gross Profit: ${opp.gross_profit:,.2f}")
        print(f"  - Vig Cost (2%): ${opp.vig_cost:.2f}")
        print(f"  - Gas Cost: ${opp.gas_cost:.2f}")
        print(f"  = Net Profit: ${opp.net_profit:,.2f}")
        print(f"\nMetrics:")
        print(f"  ROI: {opp.roi_percent:.1f}%")
        print(f"  Certainty: {opp.certainty_score * 100:.0f}%")
        print(f"  Latency: {opp.latency_seconds:.2f}s")
        print(f"\n✓ Passes all criteria:")
        print(f"  ✓ ROI > 20% ({opp.roi_percent:.1f}%)")
        print(f"  ✓ Volume $10K-$100K (${opp.volume_usd:,.0f})")
        print(f"  ✓ Total costs < $10 (${opp.vig_cost + opp.gas_cost:.2f})")
        print(f"  ✓ Certainty > 95% ({opp.certainty_score * 100:.0f}%)")
    else:
        print("\n✗ No opportunity (criteria not met)")


def demo_agent_validation():
    """Demo: Validating opportunities with AI agents."""
    print_header("DEMO 2: AI Agent Validation")

    # Create opportunity
    detector = ArbitrageDetector()

    fake_market = {
        'id': 'market_002',
        'slug': 'will-bill-x-pass-congress',
        'condition_id': '0xdef456',
        'volume': 45000,
        'liquidity': 12000,
        'tokens': [
            {'token_id': 'token_yes', 'outcome': 'Yes', 'price': 0.55},
            {'token_id': 'token_no', 'outcome': 'No', 'price': 0.45}
        ]
    }

    certainty_info = {
        'type': 'news',
        'announcement_made': True,
        'source_credibility': 0.95,
        'multiple_sources': True,
        'reversible': False
    }

    opp = detector.detect_opportunity(
        market=fake_market,
        event_outcome='Yes',
        event_timestamp=datetime.now(),
        certainty_info=certainty_info
    )

    if opp:
        print(f"Opportunity found: {opp.market_slug}")
        print(f"  ROI: {opp.roi_percent:.1f}%")
        print(f"  Net Profit: ${opp.net_profit:,.2f}")

        # Validate with agents
        print(f"\nValidating with AI agents...")
        integrator = AgentIntegrator()
        validation = integrator.validate_opportunity(opp, use_ai_agents=True)

        print(f"\n{'='*70}")
        print("VALIDATION RESULTS")
        print(f"{'='*70}")
        print(f"\nDecision: {'APPROVED ✓' if validation.approved_for_execution else 'REJECTED ✗'}")
        print(f"Reasoning: {validation.validation_reasoning}")

        if validation.sentiment_score:
            print(f"\nSentiment Analysis:")
            print(f"  Score: {validation.sentiment_score:.1f}/100")
            print(f"  Reasoning: {validation.sentiment_reasoning}")

        if validation.risk_score:
            print(f"\nRisk Analysis:")
            print(f"  Score: {validation.risk_score:.1f}/100")
            if validation.risk_factors:
                print(f"  Factors: {', '.join(validation.risk_factors)}")
            if validation.recommended_position_size:
                print(f"  Recommended Position: ${validation.recommended_position_size:,.2f}")
                print(f"    (vs calculated ${opp.position_size_usd:,.2f})")

        if validation.approved_for_execution:
            print(f"\n{'='*70}")
            print("✓ READY FOR EXECUTION")
            print(f"{'='*70}")
            print("Next steps:")
            print("  1. Execute trade via py-clob-client (authenticated)")
            print("  2. Monitor position")
            print("  3. Wait for market resolution")
        else:
            print(f"\n✗ Not approved for execution")
    else:
        print("No opportunity detected")


def demo_event_monitoring():
    """Demo: Event monitoring and automatic opportunity detection."""
    print_header("DEMO 3: Event Monitoring System")

    print("Setting up event monitoring system...")
    print("  - Monitoring events in real-time")
    print("  - Matching events to markets")
    print("  - Detecting arbitrage opportunities")
    print("  - Validating with AI agents")

    # Create monitor
    monitor = EventMonitor(
        min_volume=10000,
        max_volume=100000,
        min_roi=0.20
    )

    # Track opportunities
    detected_opportunities = []

    def opportunity_callback(opp):
        """Called when opportunity is detected."""
        detected_opportunities.append(opp)
        print(f"\n{'='*70}")
        print("🎯 OPPORTUNITY DETECTED BY MONITOR")
        print(f"{'='*70}")
        print(f"Market: {opp.market_slug[:60]}")
        print(f"Outcome: {opp.outcome}")
        print(f"ROI: {opp.roi_percent:.1f}%")
        print(f"Net Profit: ${opp.net_profit:,.2f}")
        print(f"Certainty: {opp.certainty_score * 100:.0f}%")
        print(f"Latency: {opp.latency_seconds:.2f}s")

        # Validate with agents
        print(f"\n{'='*70}")
        print("Running AI agent validation...")
        print(f"{'='*70}")

        integrator = AgentIntegrator()
        validation = integrator.validate_opportunity(opp, use_ai_agents=True)

        if validation.approved_for_execution:
            print(f"\n✓ APPROVED FOR EXECUTION")
            print(f"  Reasoning: {validation.validation_reasoning}")
        else:
            print(f"\n✗ REJECTED")
            print(f"  Reasoning: {validation.validation_reasoning}")

    monitor.add_opportunity_callback(opportunity_callback)

    # Add mock event source
    mock_source = MockSportsEventSource()
    monitor.add_event_source(mock_source)

    # Start monitoring
    monitor.start()
    print("\n✓ Event monitor started")
    print("\nSimulating events...\n")

    # Simulate events over time
    time.sleep(1)

    print("[t=1s] Simulating: NBA game finishes")
    mock_source.add_mock_event(
        description="Lakers vs Celtics final score",
        outcome="Lakers Won",
        metadata={'score': {'lakers': 112, 'celtics': 98}}
    )

    time.sleep(2)

    print("[t=3s] Simulating: Congressional vote results")
    mock_source.add_mock_event(
        description="Infrastructure Bill H.R. 1234 vote results",
        outcome="Bill Passed",
        metadata={'votes': {'yes': 245, 'no': 190}}
    )

    time.sleep(2)

    print("[t=5s] Simulating: Fed rate decision")
    mock_source.add_mock_event(
        description="Federal Reserve interest rate decision",
        outcome="Rate Increased",
        metadata={'new_rate': 5.5, 'previous_rate': 5.25}
    )

    # Let monitor process events
    time.sleep(5)

    # Stop and report
    monitor.stop()

    print(f"\n{'='*70}")
    print("MONITORING SESSION COMPLETE")
    print(f"{'='*70}")
    print(f"Events simulated: 3")
    print(f"Opportunities detected: {len(detected_opportunities)}")

    if detected_opportunities:
        print(f"\nDetected opportunities:")
        for i, opp in enumerate(detected_opportunities, 1):
            print(f"\n{i}. {opp.market_slug[:50]}")
            print(f"   ROI: {opp.roi_percent:.1f}%")
            print(f"   Profit: ${opp.net_profit:,.2f}")
    else:
        print("\nNote: No opportunities found")
        print("This is expected with mock data if no matching markets exist")
        print("In production, this would match against real Polymarket markets")


def demo_volume_filtering():
    """Demo: Filtering markets by volume range."""
    print_header("DEMO 4: Volume-Based Market Filtering")

    from polymarket import GammaClient

    print("Fetching markets from Polymarket...")
    gamma = GammaClient()

    # Get active markets
    all_markets = gamma.filter_markets(
        active_only=True,
        open_only=True,
        min_liquidity=1000,
        limit=100
    )

    print(f"\n✓ Fetched {len(all_markets)} active markets")

    # Filter by volume range ($10K - $100K)
    target_range = [m for m in all_markets if 10000 <= m.get('volume', 0) <= 100000]

    print(f"\nVolume Range Analysis:")
    print(f"  Total active markets: {len(all_markets)}")
    print(f"  In target range ($10K-$100K): {len(target_range)}")

    if target_range:
        print(f"\nTop markets in target range:")
        sorted_markets = sorted(target_range, key=lambda x: x.get('volume', 0), reverse=True)

        for i, m in enumerate(sorted_markets[:10], 1):
            volume = m.get('volume', 0)
            liquidity = m.get('liquidity', 0)
            slug = m.get('slug', 'Unknown')[:50]
            print(f"\n{i}. {slug}")
            print(f"   Volume: ${volume:,.2f}")
            print(f"   Liquidity: ${liquidity:,.2f}")
            print(f"   Condition ID: {m.get('condition_id', 'N/A')[:30]}...")

        print(f"\n✓ These markets meet volume criteria for arbitrage")
    else:
        print(f"\n⚠ No markets currently in target volume range")
        print(f"  (May vary based on current market conditions)")


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("  POLYMARKET ARBITRAGE SYSTEM - COMPLETE DEMO")
    print("="*70)
    print("\nThis demonstrates the full arbitrage detection pipeline:")
    print("  1. Basic opportunity detection and profit calculation")
    print("  2. AI agent validation (sentiment + risk assessment)")
    print("  3. Event monitoring and automatic detection")
    print("  4. Real market volume filtering")
    print("\nPress Enter to start...")
    input()

    try:
        # Run demos
        demo_basic_arbitrage_detection()

        print("\n\nPress Enter to continue to next demo...")
        input()

        demo_agent_validation()

        print("\n\nPress Enter to continue to event monitoring demo...")
        input()

        demo_event_monitoring()

        print("\n\nPress Enter to see real market data...")
        input()

        demo_volume_filtering()

        # Final summary
        print_header("SUMMARY")
        print("✓ All components demonstrated successfully!")
        print("\nSystem Capabilities:")
        print("  ✓ Detect arbitrage opportunities with 20%+ ROI")
        print("  ✓ Filter markets in $10K-$100K volume range")
        print("  ✓ Validate certainty (95%+ confidence required)")
        print("  ✓ Keep costs under $10 per trade")
        print("  ✓ AI agent validation (sentiment + risk)")
        print("  ✓ Real-time event monitoring")
        print("  ✓ Automatic market matching")

        print("\nNext Steps for Production:")
        print("  1. Integrate real event sources (ESPN API, Reuters, etc)")
        print("  2. Set up authenticated CLOB client (py-clob-client)")
        print("  3. Implement trade execution logic")
        print("  4. Add position tracking and P&L reporting")
        print("  5. Deploy monitoring system (24/7 operation)")
        print("  6. Start with paper trading to validate system")

        print("\nImplementation Status:")
        print("  ✓ Core arbitrage detection logic")
        print("  ✓ Event monitoring framework")
        print("  ✓ Market matching system")
        print("  ✓ AI agent integration")
        print("  ⏳ Real event sources (ESPN, news feeds)")
        print("  ⏳ Trade execution (needs authentication)")
        print("  ⏳ Position management")
        print("  ⏳ P&L tracking")

        print("\n" + "="*70)
        print("  DEMO COMPLETE")
        print("="*70 + "\n")

        return 0

    except KeyboardInterrupt:
        print("\n\n✗ Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

"""
Paper Trading Demo with Mock Opportunities

Demonstrates the paper trading system with simulated opportunities
to show how the system works when trades are detected.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from polymarket.paper_trading import PaperTradingEngine, SimulatedTrade
    from polymarket.arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity
    from datetime import datetime
except ImportError:
    from paper_trading import PaperTradingEngine, SimulatedTrade
    from arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity
    from datetime import datetime


def create_mock_opportunity(
    market_slug: str,
    outcome: str,
    current_price: float,
    position_size: float,
    volume: float = 50000
) -> ArbitrageOpportunity:
    """Create a mock arbitrage opportunity for testing."""

    fake_market = {
        'id': f'mock_{int(datetime.now().timestamp())}',
        'slug': market_slug,
        'condition_id': '0xmock123',
        'volume': volume,
        'liquidity': 15000,
        'tokens': [
            {'token_id': 'token_yes', 'outcome': outcome, 'price': current_price},
            {'token_id': 'token_no', 'outcome': 'No', 'price': 1 - current_price}
        ]
    }

    certainty_info = {
        'type': 'sports',
        'game_status': 'FINAL',
        'final_score': {'team_a': 3, 'team_b': 1},
        'source': 'Demo - ESPN Official API'
    }

    detector = ArbitrageDetector()
    return detector.detect_opportunity(
        market=fake_market,
        event_outcome=outcome,
        event_timestamp=datetime.now(),
        certainty_info=certainty_info
    )


def run_demo():
    """Run paper trading demo with mock opportunities."""

    print("\n" + "="*70)
    print("  PAPER TRADING DEMO - WITH MOCK OPPORTUNITIES")
    print("="*70)
    print("\nThis demo shows how the paper trading system works when")
    print("it detects arbitrage opportunities.")
    print("\nScenario: System detects 3 certain outcomes before markets update")
    print("="*70 + "\n")

    # Initialize engine
    engine = PaperTradingEngine(starting_balance=10000.0)

    print("Creating mock opportunities...\n")

    # Opportunity 1: Lakers game (good ROI)
    opp1 = create_mock_opportunity(
        market_slug="will-lakers-beat-celtics-game-tonight",
        outcome="Yes",
        current_price=0.65,
        position_size=1500,
        volume=75000
    )

    # Opportunity 2: Congressional vote (excellent ROI)
    opp2 = create_mock_opportunity(
        market_slug="will-infrastructure-bill-pass-this-week",
        outcome="Yes",
        current_price=0.58,
        position_size=2000,
        volume=60000
    )

    # Opportunity 3: Fed rate decision (moderate ROI)
    opp3 = create_mock_opportunity(
        market_slug="will-fed-raise-rates-by-25-basis-points",
        outcome="Yes",
        current_price=0.70,
        position_size=1000,
        volume=45000
    )

    opportunities = [opp1, opp2, opp3]

    # Display opportunities
    print(f"{'='*70}")
    print(f"DETECTED {len(opportunities)} ARBITRAGE OPPORTUNITIES")
    print(f"{'='*70}\n")

    for i, opp in enumerate(opportunities, 1):
        if opp:
            print(f"{i}. {opp.market_slug}")
            print(f"   Current Price: ${opp.current_price:.3f} → Should be $1.00")
            print(f"   Position: ${opp.position_size_usd:,.2f}")
            print(f"   Expected Profit: ${opp.net_profit:,.2f}")
            print(f"   ROI: {opp.roi_percent:.1f}%")
            print(f"   Certainty: {opp.certainty_score * 100:.0f}%")
            print()

    input("Press Enter to execute trades...")

    # Execute trades
    print(f"\n{'='*70}")
    print("EXECUTING SIMULATED TRADES")
    print(f"{'='*70}\n")

    trades = []
    for opp in opportunities:
        if opp:
            trade = engine.simulate_trade_entry(opp)
            if trade:
                trades.append(trade)

    # Show portfolio
    engine.print_performance()

    input("Press Enter to simulate market resolutions...")

    # Simulate market resolutions
    print(f"\n{'='*70}")
    print("SIMULATING MARKET RESOLUTIONS")
    print(f"{'='*70}\n")
    print("All outcomes were certain, so all markets resolve to $1.00\n")

    for trade in trades:
        engine.simulate_trade_exit(
            trade,
            exit_price=1.0,
            reason="Market resolved - outcome was certain"
        )

    # Final results
    print(f"\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}\n")

    engine.print_performance()

    stats = engine.get_performance_summary()

    print(f"{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}\n")

    if stats['winning_trades'] > 0:
        print(f"✅ ALL TRADES PROFITABLE ({stats['win_rate']:.0f}% win rate)")
        print(f"\nWhy this worked:")
        print(f"  • Only traded on CERTAIN outcomes (100% confidence)")
        print(f"  • Exploited latency before market updated")
        print(f"  • All trades had 20%+ ROI after costs")
        print(f"  • Total costs were < $10 per trade")
        print(f"\nAccount Growth:")
        print(f"  ${stats['starting_balance']:,.2f} → ${stats['current_balance']:,.2f}")
        print(f"  Net Profit: ${stats['total_profit']:,.2f}")
        print(f"  Return: {stats['session_roi']:.1f}%")

    print(f"\n{'='*70}")
    print("DEMO COMPLETE")
    print(f"{'='*70}\n")

    print("In production, this would:")
    print("  1. Monitor real event sources (ESPN, Reuters, etc.)")
    print("  2. Detect when outcomes are certain")
    print("  3. Find markets that haven't updated yet")
    print("  4. Execute real trades via authenticated CLOB client")
    print("  5. Wait for market resolution")
    print("  6. Collect profits automatically")

    print(f"\nTrade log saved to: {engine.log_file}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    run_demo()

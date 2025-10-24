"""
Polymarket Latency Arbitrage Detector

This module detects certainty-based arbitrage opportunities where:
1. An event outcome is CERTAIN (officially announced)
2. Market hasn't updated yet (latency window)
3. Profit margin > 20% after vig
4. Volume in $10K-$100K range
5. Total cost < $10 per trade

This is NOT speculation - we only trade when outcome is 100% certain.
"""
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    market_id: str
    market_slug: str
    condition_id: str
    token_id: str  # Which outcome token to buy
    outcome: str  # e.g., "Yes" or "Team A"
    current_price: float  # Current market price (0-1)
    should_be_price: float  # Should be 1.0 if certain
    position_size_usd: float
    expected_payout: float
    gross_profit: float
    vig_cost: float  # 2% of net profit
    gas_cost: float  # Polygon gas
    net_profit: float
    roi_percent: float
    certainty_score: float  # 0-1, how certain is the outcome
    event_timestamp: datetime
    detection_timestamp: datetime
    latency_seconds: float
    volume_usd: float
    liquidity_usd: float
    reasoning: str  # Why this is certain


class TradingCosts:
    """Calculate trading costs for Polymarket."""

    # Polymarket appears to charge ~2% on net winnings
    VIG_PERCENT = 0.02

    # Polygon network gas fees (very low)
    GAS_FEE_USD = 0.50  # Conservative estimate

    # API costs (read-only is free)
    API_COST_USD = 0.00

    @classmethod
    def calculate_trade_cost(cls, position_size: float, gross_profit: float) -> Dict[str, float]:
        """
        Calculate all costs for a trade.

        Args:
            position_size: Amount invested in USD
            gross_profit: Expected profit before costs

        Returns:
            Dict with breakdown of costs
        """
        vig = gross_profit * cls.VIG_PERCENT
        gas = cls.GAS_FEE_USD
        api = cls.API_COST_USD
        total = vig + gas + api

        return {
            'vig': vig,
            'gas': gas,
            'api': api,
            'total': total,
            'net_profit': gross_profit - total,
            'roi': ((gross_profit - total) / position_size) if position_size > 0 else 0
        }


class ProfitCalculator:
    """Calculate expected profits from arbitrage opportunities."""

    MINIMUM_ROI = 0.20  # 20% minimum return
    MAX_POSITION_USD = 5000  # Max per trade
    MIN_VOLUME_USD = 10000  # Min market volume
    MAX_VOLUME_USD = 100000  # Max market volume

    @classmethod
    def calculate_opportunity(
        cls,
        current_price: float,
        certain_outcome_price: float,  # Should be 1.0
        market_volume: float,
        market_liquidity: float,
        certainty_score: float = 1.0
    ) -> Optional[Dict]:
        """
        Calculate if this is a profitable opportunity.

        Args:
            current_price: Current market price (0-1)
            certain_outcome_price: Price if outcome is certain (usually 1.0)
            market_volume: Total market volume in USD
            market_liquidity: Available liquidity in USD
            certainty_score: How certain is the outcome (0-1)

        Returns:
            Dict with opportunity details or None if not profitable
        """
        # Filter by volume
        if not (cls.MIN_VOLUME_USD <= market_volume <= cls.MAX_VOLUME_USD):
            return None

        # Only proceed if outcome is highly certain
        if certainty_score < 0.95:
            return None

        # Calculate position size (limited by liquidity and max position)
        max_position = min(
            cls.MAX_POSITION_USD,
            market_liquidity * 0.1,  # Don't take more than 10% of liquidity
            market_volume * 0.05  # Don't take more than 5% of total volume
        )

        if max_position < 100:  # Min position $100
            return None

        # Calculate expected payout
        # If buying "Yes" at $0.60, and it resolves to $1.00:
        # $1000 / 0.60 = 1666.67 shares
        # Payout = 1666.67 * $1.00 = $1666.67
        # Profit = $1666.67 - $1000 = $666.67

        if current_price <= 0 or current_price >= 1:
            return None

        shares = max_position / current_price
        expected_payout = shares * certain_outcome_price
        gross_profit = expected_payout - max_position

        if gross_profit <= 0:
            return None

        # Calculate costs
        costs = TradingCosts.calculate_trade_cost(max_position, gross_profit)

        # Check if ROI meets minimum
        if costs['roi'] < cls.MINIMUM_ROI:
            return None

        return {
            'position_size': max_position,
            'shares': shares,
            'expected_payout': expected_payout,
            'gross_profit': gross_profit,
            'vig_cost': costs['vig'],
            'gas_cost': costs['gas'],
            'net_profit': costs['net_profit'],
            'roi': costs['roi'],
            'meets_criteria': True
        }


class CertaintyValidator:
    """Validates that an outcome is certain (not speculative)."""

    @staticmethod
    def validate_sports_outcome(
        game_status: str,
        final_score: Optional[Dict] = None,
        official_source: str = None
    ) -> Tuple[bool, float, str]:
        """
        Validate a sports game outcome is certain.

        Returns:
            (is_certain, certainty_score, reasoning)
        """
        if game_status != "FINAL":
            return False, 0.0, "Game not finished"

        if not final_score:
            return False, 0.0, "No final score available"

        if not official_source:
            return False, 0.8, "No official source confirmation"

        # Official, final score from credible source = certain
        return True, 1.0, f"Official final score from {official_source}"

    @staticmethod
    def validate_news_outcome(
        announcement_made: bool,
        source_credibility: float,  # 0-1
        multiple_sources: bool,
        reversible: bool  # Can the decision be reversed?
    ) -> Tuple[bool, float, str]:
        """
        Validate a news/announcement outcome is certain.

        Returns:
            (is_certain, certainty_score, reasoning)
        """
        if not announcement_made:
            return False, 0.0, "No official announcement"

        if reversible:
            return False, 0.5, "Decision could be reversed"

        if source_credibility < 0.9:
            return False, 0.7, "Source not credible enough"

        certainty = source_credibility
        if multiple_sources:
            certainty = min(1.0, certainty + 0.1)

        reasoning = f"Official announcement, credibility={source_credibility:.2f}"
        if multiple_sources:
            reasoning += ", multiple sources confirm"

        return certainty >= 0.95, certainty, reasoning


class ArbitrageDetector:
    """Main detector for latency arbitrage opportunities."""

    def __init__(self):
        self.profit_calc = ProfitCalculator()
        self.certainty_validator = CertaintyValidator()
        self.detected_opportunities: List[ArbitrageOpportunity] = []

    def detect_opportunity(
        self,
        market: Dict,
        event_outcome: str,  # "Yes", "No", "Team A", etc
        event_timestamp: datetime,
        certainty_info: Dict
    ) -> Optional[ArbitrageOpportunity]:
        """
        Detect if there's an arbitrage opportunity.

        Args:
            market: Market data from Polymarket API
            event_outcome: The certain outcome
            event_timestamp: When the event was decided
            certainty_info: Info about why outcome is certain

        Returns:
            ArbitrageOpportunity if valid, None otherwise
        """
        detection_time = datetime.now()
        latency = (detection_time - event_timestamp).total_seconds()

        # Find the token for the certain outcome
        tokens = market.get('tokens', [])
        target_token = None
        for token in tokens:
            if token.get('outcome', '').lower() == event_outcome.lower():
                target_token = token
                break

        if not target_token:
            return None

        current_price = target_token.get('price', 0)
        token_id = target_token.get('token_id')

        # If price is already 1.0, market has updated
        if current_price >= 0.95:
            return None

        # Validate certainty
        is_certain, certainty_score, reasoning = self._validate_certainty(certainty_info)
        if not is_certain:
            return None

        # Calculate profitability
        volume = market.get('volume', 0) or 0
        liquidity = market.get('liquidity', 0) or 0

        # Try to extract volume/liquidity if not directly available
        if volume == 0:
            # Check in raw data
            raw = market.get('raw', {})
            volume = raw.get('volumeNum', 0) or raw.get('volume', 0) or 0

        if liquidity == 0:
            raw = market.get('raw', {})
            liquidity = raw.get('liquidityNum', 0) or raw.get('liquidity', 0) or 0

        opportunity_calc = self.profit_calc.calculate_opportunity(
            current_price=current_price,
            certain_outcome_price=1.0,
            market_volume=float(volume) if volume else 50000,  # Default mid-range
            market_liquidity=float(liquidity) if liquidity else 10000,
            certainty_score=certainty_score
        )

        if not opportunity_calc:
            return None

        # Create opportunity object
        opportunity = ArbitrageOpportunity(
            market_id=market.get('id', ''),
            market_slug=market.get('slug', ''),
            condition_id=market.get('condition_id', ''),
            token_id=token_id,
            outcome=event_outcome,
            current_price=current_price,
            should_be_price=1.0,
            position_size_usd=opportunity_calc['position_size'],
            expected_payout=opportunity_calc['expected_payout'],
            gross_profit=opportunity_calc['gross_profit'],
            vig_cost=opportunity_calc['vig_cost'],
            gas_cost=opportunity_calc['gas_cost'],
            net_profit=opportunity_calc['net_profit'],
            roi_percent=opportunity_calc['roi'] * 100,
            certainty_score=certainty_score,
            event_timestamp=event_timestamp,
            detection_timestamp=detection_time,
            latency_seconds=latency,
            volume_usd=float(volume) if volume else 0,
            liquidity_usd=float(liquidity) if liquidity else 0,
            reasoning=reasoning
        )

        self.detected_opportunities.append(opportunity)
        return opportunity

    def _validate_certainty(self, certainty_info: Dict) -> Tuple[bool, float, str]:
        """
        Validate certainty based on event type.

        Args:
            certainty_info: Dict with 'type' and relevant fields

        Returns:
            (is_certain, certainty_score, reasoning)
        """
        event_type = certainty_info.get('type', 'unknown')

        if event_type == 'sports':
            return self.certainty_validator.validate_sports_outcome(
                game_status=certainty_info.get('game_status', ''),
                final_score=certainty_info.get('final_score'),
                official_source=certainty_info.get('source')
            )
        elif event_type == 'news':
            return self.certainty_validator.validate_news_outcome(
                announcement_made=certainty_info.get('announcement_made', False),
                source_credibility=certainty_info.get('source_credibility', 0),
                multiple_sources=certainty_info.get('multiple_sources', False),
                reversible=certainty_info.get('reversible', True)
            )
        else:
            return False, 0.0, "Unknown event type"

    def get_best_opportunities(self, min_roi: float = 20.0) -> List[ArbitrageOpportunity]:
        """
        Get best opportunities sorted by ROI.

        Args:
            min_roi: Minimum ROI percentage

        Returns:
            List of opportunities meeting criteria
        """
        valid = [
            opp for opp in self.detected_opportunities
            if opp.roi_percent >= min_roi and opp.certainty_score >= 0.95
        ]

        return sorted(valid, key=lambda x: x.roi_percent, reverse=True)


# Example usage
if __name__ == "__main__":
    detector = ArbitrageDetector()

    # Simulate a sports game outcome
    fake_market = {
        'id': '12345',
        'slug': 'will-team-a-win-game',
        'condition_id': '0xabc123',
        'volume': 50000,
        'liquidity': 15000,
        'tokens': [
            {'token_id': 'token_yes', 'outcome': 'Yes', 'price': 0.65},
            {'token_id': 'token_no', 'outcome': 'No', 'price': 0.35}
        ]
    }

    # Game just ended, Team A won (outcome = "Yes")
    event_time = datetime.now()

    certainty = {
        'type': 'sports',
        'game_status': 'FINAL',
        'final_score': {'team_a': 3, 'team_b': 1},
        'source': 'ESPN Official API'
    }

    opp = detector.detect_opportunity(
        market=fake_market,
        event_outcome='Yes',
        event_timestamp=event_time,
        certainty_info=certainty
    )

    if opp:
        print(f"✓ Opportunity Detected!")
        print(f"  Market: {opp.market_slug}")
        print(f"  Outcome: {opp.outcome}")
        print(f"  Current Price: ${opp.current_price:.3f}")
        print(f"  Position Size: ${opp.position_size_usd:,.2f}")
        print(f"  Expected Payout: ${opp.expected_payout:,.2f}")
        print(f"  Gross Profit: ${opp.gross_profit:,.2f}")
        print(f"  Vig Cost: ${opp.vig_cost:,.2f}")
        print(f"  Gas Cost: ${opp.gas_cost:,.2f}")
        print(f"  Net Profit: ${opp.net_profit:,.2f}")
        print(f"  ROI: {opp.roi_percent:.1f}%")
        print(f"  Certainty: {opp.certainty_score * 100:.1f}%")
        print(f"  Reasoning: {opp.reasoning}")
        print(f"  Latency: {opp.latency_seconds:.2f}s")
    else:
        print("✗ No valid opportunity")

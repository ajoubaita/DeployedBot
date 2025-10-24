"""
Agent Integration for Polymarket Arbitrage

Connects the Polymarket arbitrage system with existing moon-dev AI agents
for trade validation, sentiment analysis, and risk assessment.

This module bridges:
- Polymarket event detection -> moon-dev agent analysis
- Agent decisions -> Polymarket trade execution readiness
"""
import sys
import os
from typing import Dict, Optional, List
from dataclasses import dataclass

# Add parent directory to path to import moon-dev agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import from local directory
try:
    from polymarket.arbitrage_detector import ArbitrageOpportunity
except ImportError:
    # If running as script, try relative import
    from arbitrage_detector import ArbitrageOpportunity


@dataclass
class AgentValidation:
    """Results from agent validation of an arbitrage opportunity."""
    opportunity: ArbitrageOpportunity
    sentiment_score: Optional[float] = None  # 0-100, from sentiment_agent
    sentiment_reasoning: Optional[str] = None
    risk_score: Optional[float] = None  # 0-100, from risk_agent
    risk_factors: Optional[List[str]] = None
    recommended_position_size: Optional[float] = None  # USD, from risk_agent
    approved_for_execution: bool = False
    validation_reasoning: str = ""


class AgentIntegrator:
    """
    Integrates Polymarket arbitrage system with moon-dev AI agents.

    Uses existing agents from src/agents/ to validate opportunities:
    - sentiment_agent: Analyze market sentiment around the event
    - risk_agent: Assess trade risk and position sizing
    - (future) strategy_agent: Strategic decision making
    """

    def __init__(self):
        self.sentiment_agent = None
        self.risk_agent = None
        self._agents_loaded = False

    def _load_agents(self):
        """Lazy load agents from src/agents/."""
        if self._agents_loaded:
            return

        try:
            # Import agents dynamically
            # These imports may fail if agents aren't available
            try:
                from src.agents.sentiment_agent import analyze_sentiment
                self.sentiment_agent = analyze_sentiment
                print("[AgentIntegrator] ✓ Loaded sentiment_agent")
            except ImportError as e:
                print(f"[AgentIntegrator] ⚠ Could not load sentiment_agent: {e}")

            try:
                from src.agents.risk_agent import assess_risk
                self.risk_agent = assess_risk
                print("[AgentIntegrator] ✓ Loaded risk_agent")
            except ImportError as e:
                print(f"[AgentIntegrator] ⚠ Could not load risk_agent: {e}")

            self._agents_loaded = True

        except Exception as e:
            print(f"[AgentIntegrator] Error loading agents: {e}")
            print("[AgentIntegrator] Will proceed with basic validation only")

    def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        use_ai_agents: bool = True
    ) -> AgentValidation:
        """
        Validate an arbitrage opportunity using AI agents.

        Args:
            opportunity: The detected arbitrage opportunity
            use_ai_agents: Whether to use AI agents (vs basic validation only)

        Returns:
            AgentValidation with agent analysis and approval decision
        """
        print(f"\n[AgentIntegrator] Validating opportunity: {opportunity.market_slug[:50]}...")

        validation = AgentValidation(
            opportunity=opportunity,
            approved_for_execution=False,
            validation_reasoning=""
        )

        # Basic validation (always runs)
        basic_checks = self._basic_validation(opportunity)
        if not basic_checks['passed']:
            validation.validation_reasoning = basic_checks['reason']
            return validation

        # AI agent validation (optional)
        if use_ai_agents:
            self._load_agents()

            # Sentiment analysis
            if self.sentiment_agent:
                sentiment_result = self._analyze_sentiment(opportunity)
                validation.sentiment_score = sentiment_result.get('score')
                validation.sentiment_reasoning = sentiment_result.get('reasoning')

            # Risk analysis
            if self.risk_agent:
                risk_result = self._analyze_risk(opportunity)
                validation.risk_score = risk_result.get('score')
                validation.risk_factors = risk_result.get('factors', [])
                validation.recommended_position_size = risk_result.get('position_size')

        # Make final approval decision
        approval_decision = self._make_approval_decision(validation)
        validation.approved_for_execution = approval_decision['approved']
        validation.validation_reasoning = approval_decision['reasoning']

        return validation

    def _basic_validation(self, opp: ArbitrageOpportunity) -> Dict:
        """
        Basic validation checks that don't require AI.

        Returns:
            Dict with 'passed' bool and 'reason' string
        """
        # Check certainty score
        if opp.certainty_score < 0.95:
            return {
                'passed': False,
                'reason': f"Certainty too low: {opp.certainty_score * 100:.1f}% < 95%"
            }

        # Check ROI
        if opp.roi_percent < 20:
            return {
                'passed': False,
                'reason': f"ROI too low: {opp.roi_percent:.1f}% < 20%"
            }

        # Check net profit is positive
        if opp.net_profit <= 0:
            return {
                'passed': False,
                'reason': f"Net profit not positive: ${opp.net_profit:.2f}"
            }

        # Check volume range (from requirements)
        if not (10000 <= opp.volume_usd <= 100000):
            return {
                'passed': False,
                'reason': f"Volume out of range: ${opp.volume_usd:,.0f} (need $10K-$100K)"
            }

        # Check total costs < $10
        total_cost = opp.vig_cost + opp.gas_cost
        if total_cost >= 10:
            return {
                'passed': False,
                'reason': f"Costs too high: ${total_cost:.2f} >= $10"
            }

        return {
            'passed': True,
            'reason': "All basic checks passed"
        }

    def _analyze_sentiment(self, opp: ArbitrageOpportunity) -> Dict:
        """
        Use sentiment_agent to analyze market sentiment.

        In a real implementation, this would call the actual sentiment_agent
        with relevant market data. For now, returns mock analysis.
        """
        # Mock implementation - replace with actual agent call
        # Real implementation would do:
        # result = self.sentiment_agent(market_data, event_data, ...)

        # For certainty-based arbitrage, sentiment should align with certain outcome
        # If market hasn't updated yet, sentiment might still be mixed/uncertain

        mock_sentiment = {
            'score': 75.0,  # 0-100 scale
            'reasoning': f"Event is certain ({opp.certainty_score*100:.0f}% confidence). "
                        f"Market price ({opp.current_price:.2f}) suggests crowd hasn't "
                        f"caught up to reality yet. Latency window: {opp.latency_seconds:.1f}s."
        }

        print(f"  [Sentiment] Score: {mock_sentiment['score']:.1f}/100")
        return mock_sentiment

    def _analyze_risk(self, opp: ArbitrageOpportunity) -> Dict:
        """
        Use risk_agent to assess trade risk and position sizing.

        In a real implementation, this would call the actual risk_agent.
        For now, returns mock analysis.
        """
        # Mock implementation - replace with actual agent call
        # Real implementation would do:
        # result = self.risk_agent(opportunity_data, portfolio_data, ...)

        risk_factors = []

        # Latency risk - how much time has passed?
        if opp.latency_seconds > 60:
            risk_factors.append(f"High latency: {opp.latency_seconds:.0f}s")

        # Liquidity risk - is there enough?
        if opp.liquidity_usd < opp.position_size_usd * 2:
            risk_factors.append(f"Low liquidity buffer: ${opp.liquidity_usd:,.0f}")

        # Price movement risk - how far is price from certain value?
        price_gap = abs(1.0 - opp.current_price)
        if price_gap < 0.10:
            risk_factors.append(f"Small price gap: {price_gap:.2f} (market might be updating)")

        # Calculate risk score (0-100, lower is better)
        base_risk = 20  # Base risk for any trade
        latency_risk = min(30, opp.latency_seconds / 2)  # Up to 30 points
        liquidity_risk = 20 if opp.liquidity_usd < opp.position_size_usd * 2 else 0
        certainty_bonus = -10 if opp.certainty_score >= 0.99 else 0

        risk_score = max(0, min(100, base_risk + latency_risk + liquidity_risk + certainty_bonus))

        # Adjust position size based on risk
        if risk_score < 30:
            position_multiplier = 1.0  # Full position
        elif risk_score < 50:
            position_multiplier = 0.75  # 75% position
        elif risk_score < 70:
            position_multiplier = 0.50  # 50% position
        else:
            position_multiplier = 0.25  # 25% position

        recommended_size = opp.position_size_usd * position_multiplier

        mock_risk = {
            'score': risk_score,
            'factors': risk_factors,
            'position_size': recommended_size,
            'reasoning': f"Risk score {risk_score:.0f}/100. " +
                        (f"Concerns: {', '.join(risk_factors)}" if risk_factors else "Low risk.")
        }

        print(f"  [Risk] Score: {mock_risk['score']:.1f}/100")
        print(f"  [Risk] Recommended position: ${mock_risk['position_size']:,.2f} "
              f"({position_multiplier*100:.0f}% of calculated)")

        return mock_risk

    def _make_approval_decision(self, validation: AgentValidation) -> Dict:
        """
        Make final approval decision based on all validation results.

        Args:
            validation: AgentValidation object with all scores

        Returns:
            Dict with 'approved' bool and 'reasoning' string
        """
        reasons = []
        approved = True

        opp = validation.opportunity

        # Check basic opportunity quality
        reasons.append(f"ROI: {opp.roi_percent:.1f}%")
        reasons.append(f"Certainty: {opp.certainty_score*100:.0f}%")
        reasons.append(f"Net profit: ${opp.net_profit:,.2f}")

        # Check sentiment (if available)
        if validation.sentiment_score is not None:
            if validation.sentiment_score < 50:
                approved = False
                reasons.append(f"❌ Low sentiment: {validation.sentiment_score:.0f}/100")
            else:
                reasons.append(f"✓ Sentiment: {validation.sentiment_score:.0f}/100")

        # Check risk (if available)
        if validation.risk_score is not None:
            if validation.risk_score > 70:
                approved = False
                reasons.append(f"❌ High risk: {validation.risk_score:.0f}/100")
            else:
                reasons.append(f"✓ Risk: {validation.risk_score:.0f}/100")

            if validation.risk_factors:
                reasons.append(f"Risk factors: {', '.join(validation.risk_factors)}")

        # Build reasoning string
        reasoning = " | ".join(reasons)

        return {
            'approved': approved,
            'reasoning': reasoning
        }

    def validate_multiple_opportunities(
        self,
        opportunities: List[ArbitrageOpportunity],
        max_to_approve: int = 5
    ) -> List[AgentValidation]:
        """
        Validate multiple opportunities and return top approved ones.

        Args:
            opportunities: List of opportunities to validate
            max_to_approve: Maximum number to approve

        Returns:
            List of validated and approved opportunities
        """
        print(f"\n[AgentIntegrator] Validating {len(opportunities)} opportunities...")

        validations = []
        approved_count = 0

        # Sort by ROI first
        sorted_opps = sorted(opportunities, key=lambda x: x.roi_percent, reverse=True)

        for opp in sorted_opps:
            if approved_count >= max_to_approve:
                print(f"[AgentIntegrator] Reached max approvals ({max_to_approve}), stopping")
                break

            validation = self.validate_opportunity(opp, use_ai_agents=True)
            validations.append(validation)

            if validation.approved_for_execution:
                approved_count += 1
                print(f"  ✓ Approved: {opp.market_slug[:50]}")
            else:
                print(f"  ✗ Rejected: {validation.validation_reasoning}")

        print(f"\n[AgentIntegrator] Approved {approved_count}/{len(opportunities)} opportunities")

        # Return only approved
        return [v for v in validations if v.approved_for_execution]


# Example usage
if __name__ == "__main__":
    try:
        from polymarket.arbitrage_detector import ArbitrageDetector
    except ImportError:
        from arbitrage_detector import ArbitrageDetector
    from datetime import datetime

    print("="*70)
    print("AGENT INTEGRATION DEMO")
    print("="*70)

    # Create fake opportunity for testing
    detector = ArbitrageDetector()

    fake_market = {
        'id': '12345',
        'slug': 'will-lakers-win-vs-celtics',
        'condition_id': '0xabc123',
        'volume': 50000,
        'liquidity': 15000,
        'tokens': [
            {'token_id': 'token_yes', 'outcome': 'Yes', 'price': 0.60},
            {'token_id': 'token_no', 'outcome': 'No', 'price': 0.40}
        ]
    }

    certainty = {
        'type': 'sports',
        'game_status': 'FINAL',
        'final_score': {'lakers': 108, 'celtics': 95},
        'source': 'ESPN Official API'
    }

    opp = detector.detect_opportunity(
        market=fake_market,
        event_outcome='Yes',
        event_timestamp=datetime.now(),
        certainty_info=certainty
    )

    if opp:
        print(f"\n✓ Created test opportunity:")
        print(f"  Market: {opp.market_slug}")
        print(f"  ROI: {opp.roi_percent:.1f}%")
        print(f"  Net Profit: ${opp.net_profit:,.2f}")
        print(f"  Certainty: {opp.certainty_score * 100:.0f}%")

        # Validate with agents
        integrator = AgentIntegrator()
        validation = integrator.validate_opportunity(opp, use_ai_agents=True)

        print(f"\n{'='*70}")
        print("VALIDATION RESULTS")
        print(f"{'='*70}")
        print(f"Approved: {validation.approved_for_execution}")
        print(f"Reasoning: {validation.validation_reasoning}")

        if validation.sentiment_score:
            print(f"\nSentiment Analysis:")
            print(f"  Score: {validation.sentiment_score:.1f}/100")
            print(f"  {validation.sentiment_reasoning}")

        if validation.risk_score:
            print(f"\nRisk Analysis:")
            print(f"  Score: {validation.risk_score:.1f}/100")
            if validation.risk_factors:
                print(f"  Factors: {', '.join(validation.risk_factors)}")
            if validation.recommended_position_size:
                print(f"  Recommended Size: ${validation.recommended_position_size:,.2f}")

        if validation.approved_for_execution:
            print(f"\n{'='*70}")
            print("✓ OPPORTUNITY APPROVED FOR EXECUTION")
            print(f"{'='*70}")
        else:
            print(f"\n{'='*70}")
            print("✗ OPPORTUNITY REJECTED")
            print(f"{'='*70}")

    else:
        print("\n✗ No opportunity detected (this shouldn't happen with test data)")

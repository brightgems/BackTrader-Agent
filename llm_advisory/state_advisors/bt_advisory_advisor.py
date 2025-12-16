from llm_advisory.llm_advisor import AdvisoryAdvisor
from llm_advisory.pydantic_models import (
    LLMAdvisorDataArtefact,
    LLMAdvisorDataArtefactOutputMode,
    LLMAdvisorUpdateStateData,
)
from llm_advisory.helper.llm_prompt import compile_data_artefacts

from llm_advisory.bt_advisor import BacktraderLLMAdvisor
from llm_advisory.pydantic_models import BacktraderLLMAdvisorAdvice
from llm_advisory.observers.advisory_observer import LLMAdvisoryObserver
from llm_advisory.helper.bt_data_generation import (
    get_strategy_from_state,
    generate_broker_data,
    generate_positions_data,
    generate_strategy_data,
    generate_data_feed_data,
    generate_indicator_data,
    generate_analyzer_data,
)

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import backtrader as bt
class BaseArtefactExtractor(ABC):
    """Base class for extracting different types of artifacts"""
    
    @abstractmethod
    def can_extract(self, source: Any) -> bool:
        """Check if this extractor can handle the given source"""
        pass
    
    @abstractmethod
    def extract(self, source: Any) -> List[LLMAdvisorDataArtefact]:
        """Extract artifacts from the source"""
        pass


class StrategyDataExtractor(BaseArtefactExtractor):
    """Extract strategy-related artifacts"""
    
    def can_extract(self, source: Any) -> bool:
        return isinstance(source, bt.Strategy)
    
    def extract(self, strategy: bt.Strategy) -> List[LLMAdvisorDataArtefact]:
        artifacts = []
        
        # Extract strategy overview
        strategy_data = generate_strategy_data(strategy, add_indicators=True, add_analyzers=True)
        artifacts.append(LLMAdvisorDataArtefact(
            description="Strategy Overview",
            artefact={
                "name": strategy_data.name,
                "description": strategy_data.description,
                "instruments": strategy_data.instrument_names,
                "indicators": strategy_data.indicator_names,
                "analyzers": strategy_data.analyzer_names
            },
            output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE
        ))
        
        return artifacts


class BrokerDataExtractor(BaseArtefactExtractor):
    """Extract broker-related artifacts"""
    
    def can_extract(self, source: Any) -> bool:
        return isinstance(source, bt.Strategy)
    
    def extract(self, strategy: bt.Strategy) -> List[LLMAdvisorDataArtefact]:
        artifacts = []
        
        # Extract broker data
        broker_data = generate_broker_data(strategy)
        artifacts.append(LLMAdvisorDataArtefact(
            description="Broker Status",
            artefact={
                "Cash": f"${broker_data.cash:.2f}",
                "Portfolio Value": f"${broker_data.value:.2f}",
                "Margin Used": f"${broker_data.margin:.2f}",
                "Description": broker_data.description
            },
            output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE
        ))
        
        return artifacts


class PositionDataExtractor(BaseArtefactExtractor):
    """Extract position-related artifacts with net direction analysis"""
    
    def can_extract(self, source: Any) -> bool:
        return isinstance(source, bt.Strategy)
    
    def extract(self, strategy: bt.Strategy) -> List[LLMAdvisorDataArtefact]:
        artifacts = []
        
        # Extract positions data
        positions_data = generate_positions_data(strategy)
        
        # Calculate net position direction
        net_position_size = 0.0
        open_positions = []
        
        for data_name, position in positions_data.positions.items():
            if position.position_size != 0:
                open_positions.append({
                    "Instrument": data_name,
                    "Size": position.position_size,
                    "Direction": "Long" if position.position_size > 0 else "Short",
                    "Entry Price": f"${position.position_price:.2f}"
                })
                net_position_size += position.position_size
        
        # Add positions details
        if open_positions:
            artifacts.append(LLMAdvisorDataArtefact(
                description="Open Positions",
                artefact=open_positions,
                output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE
            ))
        
        # Add net position analysis
        net_direction = "None"
        if net_position_size > 0:
            net_direction = "Net Long"
        elif net_position_size < 0:
            net_direction = "Net Short"
        
        net_analysis = {
            "Net Position Size": net_position_size,
            "Net Direction": net_direction,
            "Number of Open Positions": len(open_positions),
            "Has Positions": len(open_positions) > 0
        }
        
        artifacts.append(LLMAdvisorDataArtefact(
            description="Net Position Analysis",
            artefact=net_analysis,
            output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE
        ))
        
        return artifacts


class MarketDataExtractor(BaseArtefactExtractor):
    """Extract market data artifacts"""
    
    def can_extract(self, source: Any) -> bool:
        return isinstance(source, bt.Strategy)
    
    def extract(self, strategy: bt.Strategy) -> List[LLMAdvisorDataArtefact]:
        artifacts = []
        
        # Extract market data for each instrument (last 5 periods)
        for data_feed in strategy.datas[:3]:  # Limit to first 3 instruments
            try:
                market_data = generate_data_feed_data(data_feed, lookback_period=5, only_close=False, add_volume=True)
                
                # Extract latest price action for summary
                if market_data.data:
                    latest = market_data.data[0]  # Latest data point
                    price_summary = {
                        "Instrument": market_data.instrument,
                        "Resolution": market_data.resolution,
                        "Latest Close": f"${latest.get('close', 'N/A')}",
                        "Day Change": self._calculate_change(market_data.data),
                        "Volume": latest.get('volume', 'N/A')
                    }
                    
                    artifacts.append(LLMAdvisorDataArtefact(
                        description=f"Price Summary - {market_data.instrument}",
                        artefact=price_summary,
                        output_mode=LLMAdvisorDataArtefactOutputMode.MARKDOWN_TABLE
                    ))
            except Exception as e:
                # Continue with other instruments if one fails
                continue
        
        return artifacts
    
    def _calculate_change(self, data: List[Dict]) -> str:
        """Calculate price change from previous close"""
        if len(data) >= 2:
            current_close = data[0].get('close', 0)
            previous_close = data[1].get('close', 0)
            if previous_close and previous_close != 0:
                change_pct = ((current_close - previous_close) / previous_close) * 100
                return f"{change_pct:+.2f}%"
        return "N/A"


ADVISOR_INSTRUCTIONS = """
You are an Advisory Advisor, an AI advisor agent specialized in generating a trading advisory
for other specialized advisors. You are the last instance that decides about the final signal.

_NOTE: All data is ordered by date in ascending order, with the latest data at the bottom.
Your advice applies to forecasting the data immediately following these inputs.

---

INPUT
You will receive data about signals:
- name: name of the advisor
- signal: generated signal from an advisor, possible values are: bullish, bearish, neutral, none
- confidence: confidence level in the generated signal as a value from 0.0 to 1.0
- reasoning: reasons for the signal decision

You will also receive comprehensive market data including:
- Strategy configuration and instruments
- Current broker status and positions
- Market data feeds with price action
- Technical indicators and analysis
- Detailed position analysis with net direction

---

TASK
1. Use all available advisors signals and market data — nothing can be ignored.
2. Analyze the net position direction and market conditions.
3. Choose exactly one signal:
   - "buy"   - open a new long position (if no position open and a bullish signal)
   - "sell"  - open a new short position (if no position open and a bearish signal)
   - "close" - close position (based on net position direction and consensus)
   - "none"  - no signal
4. Use a confidence between 0.0 and 1.0 which matches your confidence level.

---"""
ADVISOR_PROMPT = "Create your advice based on the signals and comprehensive market data below."

class BacktraderAdvisoryAdvisor(AdvisoryAdvisor, BacktraderLLMAdvisor):
    """State advisor for backtrader advisory with enhanced artifact extraction"""

    signal_model_type = BacktraderLLMAdvisorAdvice
    advisor_instructions = ADVISOR_INSTRUCTIONS
    advisor_prompt = ADVISOR_PROMPT
    
    def __init__(self, provider: str = None, model: str = None):
        super().__init__(provider, model)
        self.artifact_extractors = [
            StrategyDataExtractor(),
            BrokerDataExtractor(),
            PositionDataExtractor(),
            MarketDataExtractor()
        ]
        self.advisories_observer = []

    def init_strategy(self, strategy):
        self.advisories_observer = []
        strategy._addobserver(
            True,
            LLMAdvisoryObserver,
            advisories=self.advisories_observer,
        )

    def update_state(
        self, state: LLMAdvisorUpdateStateData
    ) -> LLMAdvisorUpdateStateData:
        self.advisor_messages_input.advisor_data = compile_data_artefacts(
            self._extract_all_artifacts(state)
        )
        new_state = super()._update_state(state)
        self.advisories_observer.append(new_state["signals"][self.advisor_name])
        return new_state

    def _extract_all_artifacts(self, state) -> List[LLMAdvisorDataArtefact]:
        """Extract artifacts using all available extractors"""
        strategy = get_strategy_from_state(state)
        artifacts = []
        
        # Use each extractor to get relevant artifacts
        for extractor in self.artifact_extractors:
            if extractor.can_extract(strategy):
                try:
                    extracted = extractor.extract(strategy)
                    artifacts.extend(extracted)
                except Exception as e:
                    # Log error but continue with other extractors
                    artifacts.append(LLMAdvisorDataArtefact(
                        description=f"Error in {extractor.__class__.__name__}",
                        artefact=f"Extraction failed: {str(e)}",
                        output_mode=LLMAdvisorDataArtefactOutputMode.TEXT
                    ))
        
        # Add advisory signal analysis
        artifacts.append(self._get_signal_data_enhanced(state))
        
        return artifacts

    def _get_signal_data_enhanced(self, state) -> LLMAdvisorDataArtefact:
        """Generate signal based on comprehensive analysis with net direction"""
        strategy = get_strategy_from_state(state)
        
        # Get comprehensive position analysis
        position_extractor = PositionDataExtractor()
        position_artifacts = position_extractor.extract(strategy)
        net_position_analysis = {}
        for artifact in position_artifacts:
            if artifact.description == "Net Position Analysis":
                net_position_analysis = artifact.artefact
                break
        
        # Analyze signals from advisory observers with enhanced metrics
        signals = self._analyze_advisory_signals_enhanced()
        
        # Determine the final advice using enhanced logic
        advice = self._determine_final_advice_enhanced(
            signals, 
            net_position_analysis,
            strategy
        )
        
        return LLMAdvisorDataArtefact(
            description=f"Final advisory from {self.advisor_name}",
            artefact=advice,
            output_mode=LLMAdvisorDataArtefactOutputMode.TEXT
        )
    
    def _analyze_advisory_signals_enhanced(self) -> dict:
        """Enhanced signal analysis with detailed metrics"""
        if not hasattr(self, 'advisories_observer') or not self.advisories_observer:
            return {"signals": [], "consensus": "none", "average_confidence": 0.0}
        
        signals = []
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        total_confidence = 0.0
        
        for advisory_data in self.advisories_observer:
            if isinstance(advisory_data, dict) and "signal" in advisory_data:
                signal = advisory_data.get("signal", "none")
                confidence = advisory_data.get("confidence", 0.0)
                reasoning = advisory_data.get("reasoning", "")
                
                signals.append({
                    "signal": signal,
                    "confidence": confidence,
                    "reasoning": reasoning
                })
                
                if signal == "bullish":
                    bullish_count += 1
                elif signal == "bearish":
                    bearish_count += 1
                elif signal == "neutral":
                    neutral_count += 1
                
                total_confidence += confidence
        
        # Determine consensus with enhanced metrics
        signal_counts = {
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": neutral_count
        }
        max_signal = max(signal_counts.items(), key=lambda x: x[1])[0] if signal_counts else "none"
        
        average_confidence = total_confidence / len(signals) if signals else 0.0
        
        return {
            "signals": signals,
            "consensus": max_signal if max(signal_counts.values()) > 0 else "none",
            "average_confidence": average_confidence,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "total_signals": len(signals)
        }
    
    def _determine_final_advice_enhanced(self, signals: dict, net_position_analysis: dict, strategy: bt.Strategy) -> dict:
        """Enhanced decision logic with net position direction analysis"""
        consensus = signals.get("consensus", "none")
        average_confidence = signals.get("average_confidence", 0.0)
        has_positions = net_position_analysis.get("Has Positions", False)
        net_direction = net_position_analysis.get("Net Direction", "None")
        net_size = net_position_analysis.get("Net Position Size", 0.0)
        
        # Enhanced decision logic considering net position direction
        if not has_positions:
            # No positions - can open new positions
            if consensus == "bullish" and average_confidence > 0.6:
                return {
                    "signal": "buy",
                    "confidence": average_confidence,
                    "reasoning": f"Buy signal based on strong {consensus} consensus ({average_confidence:.2f} confidence)"
                }
            elif consensus == "bearish" and average_confidence > 0.6:
                return {
                    "signal": "sell", 
                    "confidence": average_confidence,
                    "reasoning": f"Sell signal based on strong {consensus} consensus ({average_confidence:.2f} confidence)"
                }
        else:
            # Have positions - consider closing based on net direction and consensus
            if net_direction == "Net Long" and consensus == "bearish" and average_confidence > 0.65:
                # Strong bearish consensus while net long → close
                return {
                    "signal": "close",
                    "confidence": average_confidence,
                    "reasoning": f"Close long position due to strong bearish consensus ({average_confidence:.2f} confidence)"
                }
            elif net_direction == "Net Short" and consensus == "bullish" and average_confidence > 0.65:
                # Strong bullish consensus while net short → close
                return {
                    "signal": "close",
                    "confidence": average_confidence,
                    "reasoning": f"Close short position due to strong bullish consensus ({average_confidence:.2f} confidence)"
                }
            elif abs(net_size) > 0 and consensus in ["bullish", "bearish"] and average_confidence < 0.4:
                # Weak consensus with existing positions → consider closing if confidence is low
                return {
                    "signal": "close",
                    "confidence": 0.5,  # Medium confidence for risk management
                    "reasoning": f"Close position due to low confidence in {consensus} consensus ({average_confidence:.2f} confidence)"
                }
        
        # Default to no action with reasoning
        reason = "No clear trading signal"
        if has_positions:
            reason = f"Hold position, net {net_direction.lower()}, {consensus} consensus with {average_confidence:.2f} confidence"
        elif consensus != "none":
            reason = f"No position, {consensus} consensus but confidence ({average_confidence:.2f}) below threshold"
        
        return {
            "signal": "none",
            "confidence": average_confidence,
            "reasoning": reason
        }


    def _get_broker_and_positions_data(self, state) -> list[LLMAdvisorDataArtefact]:
        """Legacy method - now uses the new artifact extraction system"""
        return self._extract_all_artifacts(state)

from typing import Literal, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from llm_advisory.llm_advisor import (
    LLMAdvisorSignal, 
    LLMAdvisorAdvice,
    LLMAdvisorState,
    LLMAdvisorDataArtefact,
    LLMAdvisorDataArtefactOutputMode,
    LLMAdvisorUpdateStateData
)


class BacktraderLLMAdvisorSignal(LLMAdvisorSignal):
    """Signal used by backtrader advisory"""
    signal: Literal["bullish", "bearish", "neutral", "none"] = Field(
        default="none",
        description="Trading advice based on advisors signals",
    )


class BacktraderLLMAdvisorAdvice(LLMAdvisorAdvice):
    """Signal for state advice"""
    signal: Literal["buy", "sell", "close", "none"] = Field(
        default="none",
        description="Advice strategy based on advisors signals",
    )


class EnhancedSignalModel(BaseModel):
    """Enhanced signal model with comprehensive trading analysis"""
    
    # Core signal information
    signal: Literal["bullish", "bearish", "neutral", "none"] = Field(
        default="none",
        description="Primary trading signal direction"
    )
    
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence level from 0.0 (no confidence) to 1.0 (high confidence)"
    )
    
    trend_strength: Literal["weak", "medium", "strong"] = Field(
        default="weak",
        description="Strength of the identified trend"
    )
    
    time_frame: Literal["short", "medium", "long"] = Field(
        default="short",
        description="Time frame applicable for this signal"
    )
    
    # Market structure levels
    key_support_levels: List[float] = Field(
        default_factory=list,
        description="Important support price levels"
    )
    
    key_resistance_levels: List[float] = Field(
        default_factory=list,
        description="Important resistance price levels"
    )
    
    risk_level: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Risk assessment for the signal"
    )
    
    reasoning: str = Field(
        default="",
        description="Detailed reasoning behind the signal analysis"
    )
    
    # Metadata
    advisor_name: Optional[str] = Field(
        default=None,
        description="Name of the advisor that generated this signal"
    )
    
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Timestamp when the signal was generated"
    )
    
    def to_dict(self, include_metadata=True) -> dict:
        """Convert signal to dictionary format"""
        data = {
            "signal": self.signal,
            "confidence": self.confidence,
            "trend_strength": self.trend_strength,
            "time_frame": self.time_frame,
            "key_support_levels": self.key_support_levels,
            "key_resistance_levels": self.key_resistance_levels,
            "risk_level": self.risk_level,
            "reasoning": self.reasoning
        }
        
        if include_metadata:
            data.update({
                "advisor_name": self.advisor_name,
                "timestamp": self.timestamp.isoformat() if self.timestamp else None
            })
        
        return data
    
    def to_markdown_table(self) -> str:
        """Convert signal to markdown table format"""
        support_levels = ", ".join([f"{level:.2f}" for level in self.key_support_levels])
        resistance_levels = ", ".join([f"{level:.2f}" for level in self.key_resistance_levels])
        
        return f"""
| Field | Value |
|-------|-------|
| **Signal** | `{self.signal.upper()}` |
| **Confidence** | {self.confidence:.2f} |
| **Trend Strength** | {self.trend_strength.title()} |
| **Time Frame** | {self.time_frame.title()} |
| **Risk Level** | {self.risk_level.title()} |
| **Key Support Levels** | {support_levels or 'None'} |
| **Key Resistance Levels** | {resistance_levels or 'None'} |
| **Advisor** | {self.advisor_name or 'Unknown'} |
| **Timestamp** | {self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else 'Unknown'} |

**Reasoning:**
{self.reasoning}
        """.strip()


class EnhancedSignalSummary(BaseModel):
    """Summary of multiple enhanced signals"""
    
    signals: List[EnhancedSignalModel] = Field(
        default_factory=list,
        description="List of individual advisor signals"
    )
    
    consensus_signal: Literal["bullish", "bearish", "neutral", "none"] = Field(
        default="none",
        description="Weighted consensus signal based on all advisors"
    )
    
    average_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average confidence across all signals"
    )
    
    risk_assessment: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Overall risk assessment"
    )
    
    def add_signal(self, signal: EnhancedSignalModel) -> None:
        """Add a new signal to the summary"""
        self.signals.append(signal)
        self._update_consensus()
    
    def _update_consensus(self) -> None:
        """Update consensus based on current signals"""
        if not self.signals:
            return
        
        # Weight signals by confidence
        bullish_score = 0.0
        bearish_score = 0.0
        neutral_score = 0.0
        
        for signal in self.signals:
            if signal.signal == "bullish":
                bullish_score += signal.confidence
            elif signal.signal == "bearish":
                bearish_score += signal.confidence
            elif signal.signal == "neutral":
                neutral_score += signal.confidence
        
        total_score = bullish_score + bearish_score + neutral_score
        
        if total_score == 0:
            self.consensus_signal = "none"
        elif bullish_score > bearish_score and bullish_score > neutral_score:
            self.consensus_signal = "bullish"
        elif bearish_score > bullish_score and bearish_score > neutral_score:
            self.consensus_signal = "bearish"
        else:
            self.consensus_signal = "neutral"
        
        # Update average confidence
        self.average_confidence = sum(s.confidence for s in self.signals) / len(self.signals)
        
        # Update risk assessment (take the highest risk level)
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        max_risk = max([risk_levels.get(s.risk_level, 1) for s in self.signals])
        self.risk_assessment = {1: "low", 2: "medium", 3: "high"}[max_risk]


class BacktraderStrategyData(BaseModel):
    """Model for strategy data"""
    name: str
    description: str
    data_names: list[str]
    instrument_names: list[str]
    indicator_names: list[str]
    analyzer_names: list[str]


class BacktraderBrokerData(BaseModel):
    """Model for broker data"""
    description: str
    cash: float
    value: float
    margin: float


class BacktraderPositionData(BaseModel):
    """Model for position data"""
    position_size: float
    position_price: float


class BacktraderPositionsData(BaseModel):
    """Model for positions data"""
    positions: dict[str, BacktraderPositionData]


class BacktraderDataFeedData(BaseModel):
    """Model for data feed data"""
    name: str
    instrument: str
    resolution: str
    data: list[dict[str, datetime | float]]


class BacktraderIndicatorData(BaseModel):
    """Model for indicator data"""
    name: str
    data: list[dict[str, datetime | float]]


class BacktraderAnalyzerData(BaseModel):
    """Model for analyzer data"""
    name: str
    data: list[dict[str, datetime | float]]
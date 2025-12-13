"""Test functionality for llm_advisory module"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

import backtrader as bt
from llm_advisory.llm_advisor import (
    LLMAdvisor, AdvisoryAdvisor, PersonaAdvisor, 
    LLMAdvisorState, LLMAdvisorUpdateStateData, LLMAdvisorDataArtefact,
    LLMMessage, LLMAdvisorSignal, LLMAdvisorAdvice
)
from llm_advisory.llm_advisory import LLMAdvisory
from llm_advisory.pydantic_models import (
    BacktraderLLMAdvisorSignal, BacktraderLLMAdvisorAdvice
)
from llm_advisory.helper.llm_prompt import compile_data_artefacts


class TestBaseClasses(unittest.TestCase):
    """Test base class functionality"""
    
    def test_llm_advisor_creation(self):
        """Test LLMAdvisor base class creation"""
        advisor = LLMAdvisor()
        self.assertEqual(advisor.advisor_name, "BaseAdvisor")
        self.assertIsInstance(advisor.advisor_messages_input.advisor_prompt, str)
        
    def test_advisory_advisor_creation(self):
        """Test AdvisoryAdvisor creation"""
        advisor = AdvisoryAdvisor()
        self.assertEqual(advisor.signal_model_type, LLMAdvisorAdvice)
        
    def test_persona_advisor_creation(self):
        """Test PersonaAdvisor creation with custom parameters"""
        advisor = PersonaAdvisor(name="TestPersona", personality="Aggressive")
        self.assertEqual(advisor.persona_name, "TestPersona")
        self.assertEqual(advisor.personality, "Aggressive")
        
    def test_llm_advisory_creation(self):
        """Test LLMAdvisory system creation"""
        advisory = LLMAdvisory()
        self.assertEqual(len(advisory.all_advisors), 0)
        self.assertIsInstance(advisory.metadata, dict)
        
    def test_pydantic_models(self):
        """Test Pydantic model creation and validation"""
        # Test signal model
        signal = BacktraderLLMAdvisorSignal(
            signal="bullish",
            confidence=0.8,
            reasoning="Strong uptrend detected"
        )
        self.assertEqual(signal.signal, "bullish")
        self.assertEqual(signal.confidence, 0.8)
        
        # Test advice model
        advice = BacktraderLLMAdvisorAdvice(
            signal="buy",
            confidence=0.7,
            reasoning="Buy opportunity identified"
        )
        self.assertEqual(advice.signal, "buy")
        self.assertEqual(advice.confidence, 0.7)
        
    def test_llm_advisor_state(self):
        """Test LLM advisor state management"""
        message = LLMMessage(role="user", content="Test message")
        artefact = LLMAdvisorDataArtefact(
            description="Test data",
            artefact={"key": "value"},
            output_mode="text"
        )
        
        state = LLMAdvisorState(
            messages=[message],
            data=[artefact],
            metadata={"key": "value"},
            advisor_name="TestAdvisor"
        )
        
        self.assertEqual(len(state.messages), 1)
        self.assertEqual(len(state.data), 1)
        self.assertEqual(state.metadata["key"], "value")


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions"""
    
    def test_compile_data_artefacts(self):
        """Test compile_data_artefacts function"""
        # Test with empty list
        result = compile_data_artefacts([])
        self.assertEqual(result, "No data available")
        
        # Test with markdown table format
        artefact = LLMAdvisorDataArtefact(
            description="Test Table",
            artefact={
                "rows": [
                    {"col1": "value1", "col2": "value2"},
                    {"col1": "value3", "col2": "value4"}
                ]
            },
            output_mode="markdown_table"
        )
        
        result = compile_data_artefacts([artefact])
        self.assertIn("Test Table", result)
        self.assertIn("col1", result)
        self.assertIn("col2", result)
        
        # Test with text format
        artefact = LLMAdvisorDataArtefact(
            description="Test Data",
            artefact={"key": "value"},
            output_mode="text"
        )
        
        result = compile_data_artefacts([artefact])
        self.assertIn("Test Data", result)
        self.assertIn("key", result)


class TestBacktraderIntegration(unittest.TestCase):
    """Test integration with Backtrader classes"""
    
    def test_backtrader_signal_model(self):
        """Test Backtrader-specific signal model"""
        signal = BacktraderLLMAdvisorSignal(
            signal="neutral",
            confidence=0.5,
            reasoning="Market is range-bound"
        )
        
        # Test valid signal values
        valid_signals = ["bullish", "bearish", "neutral", "none"]
        self.assertIn(signal.signal, valid_signals)
        
    def test_backtrader_advice_model(self):
        """Test Backtrader-specific advice model"""
        advice = BacktraderLLMAdvisorAdvice(
            signal="close",
            confidence=0.9,
            reasoning="Close position due to market conditions"
        )
        
        # Test valid advice values
        valid_advice = ["buy", "sell", "close", "none"]
        self.assertIn(advice.signal, valid_advice)


if __name__ == '__main__':
    unittest.main()
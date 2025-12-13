"""Test imports for llm_advisory module"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

class TestLLMAdvisoryImports(unittest.TestCase):
    """Test that all llm_advisory modules can be imported correctly"""
    
    def test_bt_advisory_import(self):
        """Test bt_advisory module import"""
        import llm_advisory.bt_advisory
        self.assertTrue(hasattr(llm_advisory.bt_advisory, 'BacktraderLLMAdvisory'))
        self.assertTrue(hasattr(llm_advisory.bt_advisory, 'DATA_LOOKBACK_PERIOD'))
        
    def test_bt_advisor_import(self):
        """Test bt_advisor module import"""
        import llm_advisory.bt_advisor
        self.assertTrue(hasattr(llm_advisory.bt_advisor, 'BacktraderLLMAdvisor'))
        
    def test_state_advisors_import(self):
        """Test state advisors imports"""
        import llm_advisory.state_advisors.bt_advisory_advisor
        self.assertTrue(hasattr(llm_advisory.state_advisors.bt_advisory_advisor, 'BacktraderAdvisoryAdvisor'))
        
    def test_advisors_imports(self):
        """Test all advisor imports"""
        advisors_to_test = [
            'bt_candle_pattern_advisor',
            'bt_trend_advisor', 
            'bt_technical_analysis_advisor',
            'bt_strategy_advisor',
            'bt_reversal_advisor',
            'bt_persona_advisor',
            'bt_feedback_advisor'
        ]
        
        for advisor in advisors_to_test:
            with self.subTest(advisor=advisor):
                module = __import__(f'llm_advisory.advisors.{advisor}', fromlist=['*'])
                class_name = f'Backtrader{advisor.replace("bt_", "").title().replace("_", "")}'
                self.assertTrue(hasattr(module, class_name))
                
    def test_pydantic_models_import(self):
        """Test pydantic models import"""
        import llm_advisory.pydantic_models
        self.assertTrue(hasattr(llm_advisory.pydantic_models, 'BacktraderLLMAdvisorSignal'))
        self.assertTrue(hasattr(llm_advisory.pydantic_models, 'BacktraderLLMAdvisorAdvice'))
        
    def test_base_classes_import(self):
        """Test base classes import"""
        import llm_advisory.llm_advisor
        import llm_advisory.llm_advisory
        import llm_advisory.helper.llm_prompt
        
        # Test base classes
        self.assertTrue(hasattr(llm_advisory.llm_advisor, 'LLMAdvisor'))
        self.assertTrue(hasattr(llm_advisory.llm_advisor, 'AdvisoryAdvisor'))
        self.assertTrue(hasattr(llm_advisory.llm_advisor, 'PersonaAdvisor'))
        self.assertTrue(hasattr(llm_advisory.llm_advisory, 'LLMAdvisory'))
        self.assertTrue(hasattr(llm_advisory.helper.llm_prompt, 'compile_data_artefacts'))
        
    def test_complete_imports(self):
        """Test that all modules can be imported together without conflicts"""
        # Test importing all modules sequentially
        modules = [
            'llm_advisory.bt_advisory',
            'llm_advisory.bt_advisor',
            'llm_advisory.state_advisors.bt_advisory_advisor',
            'llm_advisory.advisors.bt_candle_pattern_advisor',
            'llm_advisory.advisors.bt_trend_advisor',
            'llm_advisory.advisors.bt_technical_analysis_advisor',
            'llm_advisory.advisors.bt_strategy_advisor',
            'llm_advisory.advisors.bt_reversal_advisor',
            'llm_advisory.advisors.bt_persona_advisor',
            'llm_advisory.advisors.bt_feedback_advisor',
            'llm_advisory.pydantic_models',
            'llm_advisory.llm_advisor',
            'llm_advisory.llm_advisory'
        ]
        
        for module_name in modules:
            with self.subTest(module=module_name):
                try:
                    __import__(module_name)
                except ImportError as e:
                    self.fail(f"Failed to import {module_name}: {e}")


if __name__ == '__main__':
    unittest.main()
"""
Tests for GamED.AI v2 Agents

Run with: pytest tests/test_agents.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Import agents
from app.agents.state import create_initial_state, AgentState
from app.agents.input_enhancer import (
    input_enhancer_agent,
    _normalize_context,
    _create_fallback_context,
    validate_pedagogical_context
)
from app.agents.router import (
    router_agent,
    _normalize_selection,
    _create_fallback_selection,
    get_template_metadata,
    get_production_ready_templates,
    TEMPLATE_REGISTRY
)


class TestInitialState:
    """Test initial state creation"""

    def test_create_initial_state_minimal(self):
        """Test creating state with minimal input"""
        state = create_initial_state(
            question_id="test-123",
            question_text="What is 2+2?"
        )

        assert state["question_id"] == "test-123"
        assert state["question_text"] == "What is 2+2?"
        assert state["question_options"] is None
        assert state["current_agent"] == "input_enhancer"
        assert state["generation_complete"] is False
        assert state["max_retries"] == 3

    def test_create_initial_state_with_options(self):
        """Test creating state with answer options"""
        state = create_initial_state(
            question_id="test-456",
            question_text="What is the capital of France?",
            question_options=["London", "Paris", "Berlin", "Madrid"]
        )

        assert state["question_options"] == ["London", "Paris", "Berlin", "Madrid"]


class TestInputEnhancerAgent:
    """Test InputEnhancer agent"""

    def test_normalize_context_valid(self):
        """Test normalizing valid LLM response"""
        raw_response = {
            "blooms_level": "apply",
            "blooms_justification": "Requires applying knowledge",
            "learning_objectives": ["Understand sorting", "Apply comparison"],
            "key_concepts": [
                {"concept": "Sorting", "description": "Arranging items", "importance": "primary"}
            ],
            "difficulty": "intermediate",
            "subject": "Computer Science",
            "common_misconceptions": [
                {"misconception": "Faster is always better", "correction": "Depends on context"}
            ],
            "prerequisites": ["Basic programming"],
            "question_intent": "Test algorithm understanding"
        }

        context = _normalize_context(raw_response)

        assert context["blooms_level"] == "apply"
        assert context["difficulty"] == "intermediate"
        assert context["subject"] == "Computer Science"
        assert "Sorting" in context["key_concepts"]

    def test_normalize_context_invalid_blooms(self):
        """Test fallback for invalid Bloom's level"""
        raw_response = {
            "blooms_level": "invalid_level",
            "difficulty": "easy"  # Also invalid
        }

        context = _normalize_context(raw_response)

        assert context["blooms_level"] == "understand"  # Fallback
        assert context["difficulty"] == "intermediate"  # Fallback

    def test_fallback_context_cs_keywords(self):
        """Test fallback context detection for CS questions"""
        context = _create_fallback_context(
            "Explain the binary search algorithm",
            None
        )

        assert context["subject"] == "Computer Science"
        assert context["blooms_level"] == "understand"

    def test_fallback_context_biology_keywords(self):
        """Test fallback context detection for biology questions"""
        context = _create_fallback_context(
            "Describe the structure of a cell membrane",
            None
        )

        assert context["subject"] == "Biology"

    @pytest.mark.asyncio
    async def test_validate_pedagogical_context_valid(self):
        """Test validation of valid context"""
        context = {
            "blooms_level": "apply",
            "subject": "Mathematics",
            "difficulty": "intermediate",
            "learning_objectives": ["Solve equations"]
        }

        result = await validate_pedagogical_context(context)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_pedagogical_context_invalid(self):
        """Test validation catches invalid context"""
        context = {
            "blooms_level": "invalid",
            "difficulty": "super_hard"
        }

        result = await validate_pedagogical_context(context)

        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestRouterAgent:
    """Test Router agent"""

    def test_template_registry_complete(self):
        """Verify all expected templates are in registry"""
        expected_templates = [
            "PARAMETER_PLAYGROUND",
            "SEQUENCE_BUILDER",
            "BUCKET_SORT",
            "INTERACTIVE_DIAGRAM",
            "TIMELINE_ORDER",
            "MATCH_PAIRS"
        ]

        for template in expected_templates:
            assert template in TEMPLATE_REGISTRY

    def test_get_production_ready_templates(self):
        """Test getting production-ready templates"""
        ready = get_production_ready_templates()

        assert "PARAMETER_PLAYGROUND" in ready
        assert "SEQUENCE_BUILDER" in ready
        assert "BUCKET_SORT" in ready

    def test_normalize_selection_valid(self):
        """Test normalizing valid routing result"""
        raw_result = {
            "template_type": "SEQUENCE_BUILDER",
            "confidence": 0.85,
            "reasoning": "Steps need to be ordered",
            "alternatives": [],
            "bloom_alignment_score": 0.9,
            "subject_fit_score": 0.8,
            "interaction_fit_score": 0.85
        }

        selection = _normalize_selection(raw_result)

        assert selection["template_type"] == "SEQUENCE_BUILDER"
        assert selection["confidence"] == 0.85
        assert selection["is_production_ready"] is True

    def test_normalize_selection_invalid_template(self):
        """Test fallback for invalid template"""
        raw_result = {
            "template_type": "INVALID_TEMPLATE",
            "confidence": 0.9
        }

        selection = _normalize_selection(raw_result)

        assert selection["template_type"] == "PARAMETER_PLAYGROUND"  # Fallback

    def test_fallback_selection_sequence_keywords(self):
        """Test fallback selection for sequence questions"""
        selection = _create_fallback_selection(
            "Arrange the following steps in order",
            None,
            {"blooms_level": "understand"}
        )

        assert selection["template_type"] == "SEQUENCE_BUILDER"
        assert selection["confidence"] == 0.6

    def test_fallback_selection_categorize_keywords(self):
        """Test fallback selection for categorization questions"""
        selection = _create_fallback_selection(
            "Categorize these elements into metals and non-metals",
            ["Iron", "Carbon", "Oxygen"],
            {"blooms_level": "apply"}
        )

        assert selection["template_type"] == "BUCKET_SORT"

    def test_get_template_metadata(self):
        """Test getting template metadata"""
        meta = get_template_metadata("PARAMETER_PLAYGROUND")

        assert meta["production_ready"] is True
        assert "programming" in meta["domains"]
        assert "apply" in meta["blooms_alignment"]


class TestAgentIntegration:
    """Integration tests for agent flow"""

    @pytest.mark.asyncio
    async def test_input_enhancer_with_mock_llm(self):
        """Test InputEnhancer with mocked LLM"""
        mock_response = {
            "blooms_level": "analyze",
            "blooms_justification": "Requires analysis",
            "learning_objectives": ["Compare algorithms"],
            "key_concepts": ["Time complexity"],
            "difficulty": "advanced",
            "subject": "Computer Science",
            "common_misconceptions": [],
            "prerequisites": ["Basic algorithms"],
            "question_intent": "Algorithm comparison"
        }

        with patch('app.agents.input_enhancer.get_llm_service') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.generate_json = AsyncMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            state = create_initial_state(
                question_id="test-1",
                question_text="Compare bubble sort and quick sort"
            )

            result = await input_enhancer_agent(state)

            assert result["pedagogical_context"]["blooms_level"] == "analyze"
            assert result["pedagogical_context"]["subject"] == "Computer Science"

    @pytest.mark.asyncio
    async def test_router_with_mock_llm(self):
        """Test Router with mocked LLM"""
        mock_response = {
            "template_type": "PARAMETER_PLAYGROUND",
            "confidence": 0.9,
            "reasoning": "Algorithm visualization fits",
            "alternatives": [],
            "bloom_alignment_score": 0.9,
            "subject_fit_score": 0.95,
            "interaction_fit_score": 0.85
        }

        with patch('app.agents.router.get_llm_service') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.generate_json = AsyncMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            state = create_initial_state(
                question_id="test-2",
                question_text="Demonstrate binary search"
            )
            state["pedagogical_context"] = {
                "blooms_level": "apply",
                "subject": "Computer Science",
                "difficulty": "intermediate",
                "learning_objectives": ["Understand binary search"],
                "key_concepts": ["Divide and conquer"]
            }

            result = await router_agent(state)

            assert result["template_selection"]["template_type"] == "PARAMETER_PLAYGROUND"
            assert result["template_selection"]["confidence"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

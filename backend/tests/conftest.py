"""
Pytest configuration and fixtures for GamED.AI v2 tests
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_question():
    """Sample question for testing"""
    return {
        "id": "test-question-1",
        "text": "Explain the time complexity of binary search and demonstrate how it works on a sorted array.",
        "options": None
    }


@pytest.fixture
def sample_question_with_options():
    """Sample multiple choice question for testing"""
    return {
        "id": "test-question-2",
        "text": "Which data structure uses LIFO principle?",
        "options": ["Queue", "Stack", "Linked List", "Tree"]
    }


@pytest.fixture
def sample_pedagogical_context():
    """Sample pedagogical context for testing"""
    return {
        "blooms_level": "apply",
        "blooms_justification": "Requires applying algorithm knowledge",
        "learning_objectives": [
            "Understand binary search algorithm",
            "Analyze time complexity"
        ],
        "key_concepts": ["Binary search", "Time complexity", "Divide and conquer"],
        "difficulty": "intermediate",
        "difficulty_justification": "Requires understanding of logarithmic complexity",
        "subject": "Computer Science",
        "cross_cutting_subjects": ["Mathematics"],
        "common_misconceptions": [
            {
                "misconception": "Binary search works on unsorted arrays",
                "correction": "Array must be sorted",
                "why_common": "Students forget the prerequisite"
            }
        ],
        "prerequisites": ["Basic array operations", "Comparison operators"],
        "question_intent": "Test understanding of efficient search algorithms"
    }


@pytest.fixture
def sample_template_selection():
    """Sample template selection for testing"""
    return {
        "template_type": "PARAMETER_PLAYGROUND",
        "confidence": 0.85,
        "reasoning": "Algorithm visualization with adjustable parameters",
        "alternatives": [
            {
                "template_type": "STATE_TRACER_CODE",
                "confidence": 0.7,
                "why_not_primary": "Less interactive"
            }
        ],
        "bloom_alignment_score": 0.9,
        "subject_fit_score": 0.85,
        "interaction_fit_score": 0.8,
        "is_production_ready": True,
        "requires_code_generation": False
    }

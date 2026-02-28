"""Test that all imports work correctly"""

def test_imports():
    from app.config.models import MODEL_REGISTRY, ModelProvider, get_model_config
    from app.config.agent_models import get_agent_config, PRESET_CONFIGS
    from app.services.llm_service import LLMService, get_llm_service

    # Test model registry
    print('=== Model Registry ===')
    for key in ['groq-llama3-70b', 'claude-sonnet', 'gpt-4o']:
        config = MODEL_REGISTRY.get(key)
        if config:
            print(f'{key}: {config.provider.value}, cost=${config.cost_per_1k_output}/1k output')

    # Test presets
    print()
    print('=== Agent Presets ===')
    for preset_name in ['groq_free', 'balanced', 'cost_optimized']:
        config = PRESET_CONFIGS.get(preset_name)
        if config:
            print(f'{preset_name}: default_model={config.default_model}')

    # Test LLM service initialization (without API keys)
    print()
    print('=== LLM Service ===')
    service = LLMService()
    print(f'OpenAI client: {"initialized" if service.openai_client else "not configured"}')
    print(f'Anthropic client: {"initialized" if service.anthropic_client else "not configured"}')
    print(f'Groq client: {"initialized" if service.groq_client else "not configured"}')

    print()
    print('All imports successful!')


if __name__ == "__main__":
    test_imports()

#!/usr/bin/env python3
"""
API Provider Connectivity Test Script

Tests connectivity to all providers used in the multi-provider pipeline:
1. Ollama (Qwen) - http://localhost:11434
2. Anthropic (Claude) - ANTHROPIC_API_KEY
3. Google Gemini - GOOGLE_API_KEY
   - gemini-2.0-flash-preview (vision)
   - imagen-3.0-generate-002 (image generation)

Usage:
    PYTHONPATH=. python scripts/test_api_providers.py
"""

import asyncio
import os
import sys
import json
import httpx
from typing import Optional, Tuple
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_result(name: str, success: bool, message: str, details: Optional[str] = None):
    """Print a formatted result"""
    status = f"{Colors.GREEN}PASS{Colors.RESET}" if success else f"{Colors.RED}FAIL{Colors.RESET}"
    print(f"  [{status}] {name}")
    print(f"       {message}")
    if details:
        for line in details.split('\n'):
            print(f"       {Colors.CYAN}{line}{Colors.RESET}")


async def test_ollama(base_url: str = "http://localhost:11434") -> Tuple[bool, str]:
    """
    Test Ollama connectivity and model availability.

    Returns:
        (success, message)
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if Ollama is running
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code != 200:
                return False, f"Ollama not responding (status {response.status_code})"

            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            # Check for required models
            required_models = ["qwen2.5:7b", "llama3.2"]
            found_models = []
            missing_models = []

            for req in required_models:
                # Check if any model starts with the required prefix
                if any(m.startswith(req.split(":")[0]) for m in models):
                    found_models.append(req)
                else:
                    missing_models.append(req)

            if missing_models:
                return False, f"Missing models: {', '.join(missing_models)}. Found: {', '.join(models[:5])}"

            # Test a simple generation with qwen
            test_model = "qwen2.5:7b" if "qwen2.5:7b" in models else models[0]
            gen_response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": test_model,
                    "prompt": "Say 'test successful' and nothing else.",
                    "stream": False,
                    "options": {"num_predict": 20}
                },
                timeout=60.0
            )

            if gen_response.status_code != 200:
                return False, f"Generation failed (status {gen_response.status_code})"

            gen_data = gen_response.json()
            response_text = gen_data.get("response", "")[:50]

            return True, f"Connected. Models: {', '.join(models[:3])}. Test response: '{response_text}...'"

    except httpx.ConnectError:
        return False, "Cannot connect to Ollama. Is it running? Try: ollama serve"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_anthropic() -> Tuple[bool, str]:
    """
    Test Anthropic API connectivity.

    Returns:
        (success, message)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "ANTHROPIC_API_KEY not set in environment"

    if api_key.startswith("sk-ant-your") or api_key == "your-anthropic-key-here":
        return False, "ANTHROPIC_API_KEY is a placeholder, not a real key"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Test with a simple message
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "Say 'test successful' and nothing else."}
            ]
        )

        response_text = message.content[0].text if message.content else ""
        model_used = message.model
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        return True, f"Connected. Model: {model_used}, Tokens: {input_tokens}+{output_tokens}. Response: '{response_text[:30]}...'"

    except anthropic.AuthenticationError:
        return False, "Invalid API key (authentication failed)"
    except anthropic.APIError as e:
        return False, f"API error: {str(e)}"
    except ImportError:
        return False, "anthropic package not installed. Run: pip install anthropic"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_anthropic_opus() -> Tuple[bool, str]:
    """
    Test Anthropic Claude Opus specifically (for orchestration tasks).

    Returns:
        (success, message)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "ANTHROPIC_API_KEY not set"

    if api_key.startswith("sk-ant-your") or api_key == "your-anthropic-key-here":
        return False, "ANTHROPIC_API_KEY is a placeholder"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Test Opus model
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "Say 'opus test successful' and nothing else."}
            ]
        )

        response_text = message.content[0].text if message.content else ""

        return True, f"Opus accessible. Response: '{response_text[:40]}...'"

    except anthropic.NotFoundError:
        return False, "Opus model not available on this account/tier"
    except anthropic.AuthenticationError:
        return False, "Invalid API key"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_gemini_vision() -> Tuple[bool, str]:
    """
    Test Google Gemini Vision API (gemini-2.0-flash-preview).

    Returns:
        (success, message)
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return False, "GOOGLE_API_KEY not set in environment"

    if api_key == "your-google-api-key-here":
        return False, "GOOGLE_API_KEY is a placeholder, not a real key"

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Test with gemini-2.0-flash for vision tasks
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        response = model.generate_content(
            "Say 'gemini vision test successful' and nothing else.",
            generation_config={"max_output_tokens": 50}
        )

        response_text = response.text if response.text else ""

        return True, f"Gemini Vision connected. Response: '{response_text[:40]}...'"

    except ImportError:
        return False, "google-generativeai package not installed. Run: pip install google-generativeai"
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return False, "Invalid API key"
        if "PERMISSION_DENIED" in error_msg:
            return False, "API key doesn't have permission for this model"
        return False, f"Error: {error_msg[:100]}"


async def test_gemini_imagen() -> Tuple[bool, str]:
    """
    Test Google Gemini Imagen API (imagen-3.0-generate-002 or nano-banana-pro).

    Returns:
        (success, message)
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return False, "GOOGLE_API_KEY not set in environment"

    if api_key == "your-google-api-key-here":
        return False, "GOOGLE_API_KEY is a placeholder"

    try:
        # Try using the Vertex AI approach for Imagen
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # List available models to check for imagen
        # Note: imagen-3.0-generate-002 might require specific access

        # Try a simple image generation test
        # Using a non-destructive test prompt
        try:
            response = client.models.generate_image(
                model="imagen-3.0-generate-002",
                prompt="A simple educational diagram of a circle, clean white background, minimalist style",
                config=types.GenerateImageConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                )
            )

            if response.generated_images:
                img_size = len(response.generated_images[0].image.image_bytes) if response.generated_images[0].image else 0
                return True, f"Imagen connected. Generated image size: {img_size} bytes"
            else:
                return False, "Imagen returned no images"

        except Exception as img_error:
            # Try alternative model name
            error_str = str(img_error)
            if "not found" in error_str.lower() or "invalid" in error_str.lower():
                return False, f"Imagen model not available. Error: {error_str[:80]}"
            return False, f"Imagen error: {error_str[:100]}"

    except ImportError:
        return False, "google-genai package not installed. Run: pip install google-genai"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


async def test_serper() -> Tuple[bool, str]:
    """
    Test Serper API for web search (used by domain_knowledge_retriever).

    Returns:
        (success, message)
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return False, "SERPER_API_KEY not set in environment"

    if api_key == "your-serper-api-key-here":
        return False, "SERPER_API_KEY is a placeholder"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": "parts of a flower diagram", "num": 1}
            )

            if response.status_code != 200:
                return False, f"API error (status {response.status_code})"

            data = response.json()
            organic_count = len(data.get("organic", []))

            return True, f"Connected. Found {organic_count} results for test query."

    except Exception as e:
        return False, f"Error: {str(e)}"


async def test_serper_images() -> Tuple[bool, str]:
    """
    Test Serper Image Search API (used by diagram_image_retriever).

    Returns:
        (success, message)
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return False, "SERPER_API_KEY not set"

    if api_key == "your-serper-api-key-here":
        return False, "SERPER_API_KEY is a placeholder"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": "flower diagram labeled educational", "num": 3}
            )

            if response.status_code != 200:
                return False, f"API error (status {response.status_code})"

            data = response.json()
            images = data.get("images", [])

            if not images:
                return False, "No images returned"

            return True, f"Connected. Found {len(images)} images for test query."

    except Exception as e:
        return False, f"Error: {str(e)}"


async def run_all_tests():
    """Run all API provider tests"""
    print_header("API Provider Connectivity Tests")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  Working Directory: {os.getcwd()}")
    print()

    results = []

    # Test 1: Ollama (Qwen for scene generation)
    print_header("1. Ollama (Local LLM)")
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"  URL: {ollama_url}")
    success, message = await test_ollama(ollama_url)
    print_result("Ollama Connectivity", success, message)
    results.append(("Ollama", success))

    # Test 2: Anthropic (Claude)
    print_header("2. Anthropic (Claude)")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    print(f"  API Key Set: {has_key}")

    # Test Sonnet
    success, message = await test_anthropic()
    print_result("Claude Sonnet (claude-3-5-sonnet)", success, message)
    results.append(("Anthropic Sonnet", success))

    # Test Opus
    if success:  # Only test Opus if Sonnet works
        opus_success, opus_message = await test_anthropic_opus()
        print_result("Claude Opus (claude-3-opus)", opus_success, opus_message)
        results.append(("Anthropic Opus", opus_success))

    # Test 3: Google Gemini
    print_header("3. Google Gemini")
    has_key = bool(os.environ.get("GOOGLE_API_KEY"))
    print(f"  API Key Set: {has_key}")

    # Test Gemini Vision
    success, message = await test_gemini_vision()
    print_result("Gemini Vision (gemini-2.0-flash)", success, message)
    results.append(("Gemini Vision", success))

    # Test Gemini Imagen
    imagen_success, imagen_message = await test_gemini_imagen()
    print_result("Gemini Imagen (image generation)", imagen_success, imagen_message)
    results.append(("Gemini Imagen", imagen_success))

    # Test 4: Serper (Web Search)
    print_header("4. Serper (Web Search)")
    has_key = bool(os.environ.get("SERPER_API_KEY"))
    print(f"  API Key Set: {has_key}")

    success, message = await test_serper()
    print_result("Serper Web Search", success, message)
    results.append(("Serper Web", success))

    success, message = await test_serper_images()
    print_result("Serper Image Search", success, message)
    results.append(("Serper Images", success))

    # Summary
    print_header("Summary")
    passed = sum(1 for _, s in results if s)
    total = len(results)

    for name, success in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if success else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{status}] {name}")

    print()
    if passed == total:
        print(f"  {Colors.GREEN}{Colors.BOLD}All {total} tests passed!{Colors.RESET}")
        print(f"  Pipeline is ready to use the multi-provider architecture.")
    else:
        print(f"  {Colors.YELLOW}{passed}/{total} tests passed{Colors.RESET}")
        print(f"  {Colors.RED}{total - passed} services need attention{Colors.RESET}")

        # Provide recommendations
        failed_services = [name for name, success in results if not success]
        print(f"\n  {Colors.BOLD}Recommendations:{Colors.RESET}")

        if "Ollama" in failed_services:
            print(f"    - Start Ollama: {Colors.CYAN}ollama serve{Colors.RESET}")
            print(f"    - Pull required models: {Colors.CYAN}ollama pull qwen2.5:7b{Colors.RESET}")

        if any("Anthropic" in s for s in failed_services):
            print(f"    - Set ANTHROPIC_API_KEY in .env")
            print(f"    - Get key from: https://console.anthropic.com/")

        if any("Gemini" in s for s in failed_services):
            print(f"    - Set GOOGLE_API_KEY in .env")
            print(f"    - Get key from: https://aistudio.google.com/app/apikey")
            print(f"    - Enable Imagen API if needed")

        if any("Serper" in s for s in failed_services):
            print(f"    - Set SERPER_API_KEY in .env")
            print(f"    - Get key from: https://serper.dev/")

    print()
    return passed == total


if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

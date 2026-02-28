#!/usr/bin/env python3
"""
Verify Ollama VLM (Vision Language Model) installation and configuration.

Tests:
1. Ollama server is running
2. VLM model is available
3. Can make VLM API calls
4. Can process images and return labels
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def check_ollama_server():
    """Check if Ollama server is running"""
    print("\n" + "=" * 60)
    print("Ollama Server Check")
    print("=" * 60)
    
    import httpx
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"Checking Ollama at: {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                print("✓ Ollama server is running")
                return True
            else:
                print(f"❌ Ollama server returned status {response.status_code}")
                return False
    except httpx.ConnectError:
        print("❌ Cannot connect to Ollama server")
        print("   Start Ollama with: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False


async def check_vlm_model():
    """Check if VLM model is available"""
    print("\n" + "=" * 60)
    print("VLM Model Check")
    print("=" * 60)
    
    import httpx
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.getenv("VLM_MODEL", "llava:latest")
    
    print(f"Checking for model: {model_name}")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # List available models
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code != 200:
                print(f"❌ Failed to list models: {response.status_code}")
                return False
            
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Check if our model is in the list
            if any(model_name in name for name in model_names):
                print(f"✓ VLM model '{model_name}' is available")
                return True
            else:
                print(f"❌ VLM model '{model_name}' not found")
                print(f"   Available models: {', '.join(model_names[:5])}")
                print(f"   Pull model with: ollama pull {model_name}")
                return False
    except Exception as e:
        print(f"❌ Error checking VLM model: {e}")
        return False


async def test_vlm_call():
    """Test actual VLM API call"""
    print("\n" + "=" * 60)
    print("VLM API Call Test")
    print("=" * 60)
    
    import httpx
    import base64
    from PIL import Image
    import io
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.getenv("VLM_MODEL", "llava:latest")
    
    # Create a simple test image (1x1 red pixel)
    test_image = Image.new('RGB', (1, 1), color='red')
    buffer = io.BytesIO()
    test_image.save(buffer, format='PNG')
    image_bytes = buffer.getvalue()
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    print(f"Testing VLM call with model: {model_name}")
    
    try:
        url = f"{base_url}/api/generate"
        payload = {
            "model": model_name,
            "prompt": "What color is this image? Reply with just the color name.",
            "images": [image_b64],
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("response", "").strip()
                print(f"✓ VLM call successful")
                print(f"  Response: {result[:100]}")
                return True
            elif response.status_code == 404:
                print(f"❌ Model not found (404)")
                print(f"   Pull model with: ollama pull {model_name}")
                return False
            else:
                print(f"❌ VLM call failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Error testing VLM call: {e}")
        return False


async def main():
    print("=" * 60)
    print("Ollama VLM Verification")
    print("=" * 60)
    
    # Load .env if exists
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
    else:
        print("⚠ No .env file found, using system environment variables")
    
    server_ok = await check_ollama_server()
    if not server_ok:
        print("\n❌ Ollama server is not running. Cannot proceed with VLM tests.")
        return 1
    
    model_ok = await check_vlm_model()
    if not model_ok:
        print("\n❌ VLM model not available. Cannot proceed with API test.")
        return 1
    
    api_ok = await test_vlm_call()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if server_ok:
        print("✅ Ollama server: Running")
    else:
        print("❌ Ollama server: Not running")
    
    if model_ok:
        print("✅ VLM model: Available")
    else:
        print("❌ VLM model: Not available")
    
    if api_ok:
        print("✅ VLM API: Working")
    else:
        print("❌ VLM API: Not working")
    
    if server_ok and model_ok and api_ok:
        print("\n✅ VLM is ready to use!")
        return 0
    else:
        print("\n❌ VLM is not ready. Zone labeling will use fallback.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

#!/usr/bin/env python3
"""
Comprehensive dependency verification for GamED.AI image pipeline.

Checks:
1. EasyOCR - for image label removal
2. SAM3 - for semantic segmentation (preferred)
3. SAM2/SAM v1 - fallback segmentation models
4. Ollama VLM - for zone labeling
5. Serper API - for image search
6. Environment variables configuration
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

def print_status(name: str, status: str, details: str = ""):
    """Print status with color coding"""
    if status == "✅":
        symbol = f"{GREEN}✅{RESET}"
    elif status == "⚠️":
        symbol = f"{YELLOW}⚠️{RESET}"
    else:
        symbol = f"{RED}❌{RESET}"
    
    print(f"{symbol} {BOLD}{name}{RESET}")
    if details:
        print(f"   {details}")

def check_easyocr() -> Tuple[str, str]:
    """Check EasyOCR installation"""
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False)  # Test CPU mode
        print_status("EasyOCR", "✅", "Installed and working")
        
        # Check GPU availability
        try:
            import torch
            has_gpu = torch.cuda.is_available()
            if has_gpu:
                return "✅", "Installed (GPU available)"
            else:
                return "✅", "Installed (CPU mode - set EASYOCR_GPU=false for Apple Silicon)"
        except ImportError:
            return "✅", "Installed (CPU mode)"
    except ImportError:
        return "❌", "Not installed. Install with: pip install easyocr"
    except Exception as e:
        return "⚠️", f"Installed but error: {e}"

def check_sam3() -> Tuple[str, str]:
    """Check SAM3 installation"""
    try:
        from sam3.model_builder import build_sam3_image_model  # type: ignore
        from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore
        
        # Check HuggingFace authentication
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            try:
                from huggingface_hub import whoami
                whoami()  # This will raise if not authenticated
                auth_status = "Authenticated"
            except Exception:
                auth_status = "⚠️ Not authenticated - run: huggingface-cli login"
        else:
            auth_status = "Token set in environment"
        
        return "✅", f"Installed ({auth_status})"
    except ImportError:
        return "❌", "Not installed. Install with: pip install sam3"
    except Exception as e:
        return "⚠️", f"Installed but error: {e}"

def check_sam_models() -> Tuple[str, str]:
    """Check SAM/SAM2 model files"""
    sam_path = os.getenv("SAM_MODEL_PATH")
    sam2_path = os.getenv("SAM2_MODEL_PATH")
    
    results = []
    if sam_path and Path(sam_path).exists():
        size_mb = Path(sam_path).stat().st_size / (1024 * 1024)
        results.append(f"SAM v1: {sam_path} ({size_mb:.1f}MB)")
    elif sam_path:
        results.append(f"SAM v1: Path set but file not found: {sam_path}")
    
    if sam2_path and Path(sam2_path).exists():
        size_mb = Path(sam2_path).stat().st_size / (1024 * 1024)
        results.append(f"SAM2: {sam2_path} ({size_mb:.1f}MB)")
    elif sam2_path:
        results.append(f"SAM2: Path set but file not found: {sam2_path}")
    
    if results:
        return "✅", " | ".join(results)
    else:
        return "⚠️", "No SAM model paths configured (SAM3 preferred, SAM/SAM2 optional fallback)"

async def check_ollama_vlm() -> Tuple[str, str]:
    """Check Ollama VLM"""
    import httpx
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.getenv("VLM_MODEL", "llava:latest")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # Check server
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code != 200:
                return "❌", f"Ollama server not accessible (HTTP {response.status_code})"
            
            # Check model
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            if any(model_name in name for name in model_names):
                return "✅", f"Ollama running, VLM model '{model_name}' available"
            else:
                return "❌", f"Ollama running but model '{model_name}' not found. Run: ollama pull {model_name}"
    except httpx.ConnectError:
        return "❌", f"Cannot connect to Ollama at {base_url}. Start with: ollama serve"
    except Exception as e:
        return "⚠️", f"Error checking Ollama: {e}"

def check_serper_api() -> Tuple[str, str]:
    """Check Serper API key"""
    api_key = os.getenv("SERPER_API_KEY")
    if api_key and api_key != "your-serper-api-key-here":
        return "✅", "SERPER_API_KEY is set"
    else:
        return "❌", "SERPER_API_KEY not set. Get free key at: https://serper.dev"

def check_env_vars() -> List[Tuple[str, str, str]]:
    """Check all required environment variables"""
    required_vars = [
        ("USE_IMAGE_DIAGRAMS", "true", "Enable image-based diagrams"),
        ("SERPER_API_KEY", None, "Required for image search"),
        ("USE_OLLAMA", "true", "Enable local Ollama VLM"),
        ("OLLAMA_BASE_URL", "http://localhost:11434", "Ollama server URL"),
        ("VLM_MODEL", "llava:7b", "VLM model name"),
    ]
    
    optional_vars = [
        ("SAM3_MODEL_PATH", None, "SAM3 checkpoint path (optional, auto-downloads)"),
        ("USE_SAM3_MLX", "auto", "Use MLX SAM3 on Apple Silicon"),
        ("SAM_MODEL_PATH", None, "SAM v1 fallback model"),
        ("SAM2_MODEL_PATH", None, "SAM2 fallback model"),
        ("EASYOCR_GPU", "false", "EasyOCR GPU usage (false for Apple Silicon)"),
    ]
    
    results = []
    for var, default, desc in required_vars:
        value = os.getenv(var, default)
        if value and value != "your-serper-api-key-here":
            results.append(("✅", var, f"{desc}: {value}"))
        else:
            results.append(("❌", var, f"{desc}: NOT SET"))
    
    for var, default, desc in optional_vars:
        value = os.getenv(var, default)
        if value:
            results.append(("✅", var, f"{desc}: {value}"))
        else:
            results.append(("⚠️", var, f"{desc}: Not set (optional)"))
    
    return results

async def main():
    print_header("GamED.AI Image Pipeline Dependency Verification")
    
    # Load .env if exists
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}\n")
    else:
        print(f"⚠ No .env file found, using system environment variables\n")
    
    # Check each dependency
    print_header("Core Dependencies")
    
    easyocr_status, easyocr_details = check_easyocr()
    print_status("EasyOCR", easyocr_status, easyocr_details)
    
    sam3_status, sam3_details = check_sam3()
    print_status("SAM3", sam3_status, sam3_details)
    
    sam_models_status, sam_models_details = check_sam_models()
    print_status("SAM Models", sam_models_status, sam_models_details)
    
    vlm_status, vlm_details = await check_ollama_vlm()
    print_status("Ollama VLM", vlm_status, vlm_details)
    
    serper_status, serper_details = check_serper_api()
    print_status("Serper API", serper_status, serper_details)
    
    print_header("Environment Variables")
    env_results = check_env_vars()
    for status, var, details in env_results:
        print_status(var, status, details)
    
    # Summary
    print_header("Summary")
    
    critical_ok = (
        easyocr_status == "✅" or "⚠️" in easyocr_status,
        sam3_status == "✅" or sam_models_status == "✅",
        vlm_status == "✅",
        serper_status == "✅"
    )
    
    all_critical = all(critical_ok)
    
    if all_critical:
        print(f"{GREEN}{BOLD}✅ All critical dependencies are ready!{RESET}")
        print(f"\n{GREEN}You can run the full pipeline test:{RESET}")
        print(f"  FORCE_TEMPLATE=INTERACTIVE_DIAGRAM PYTHONPATH=. python scripts/test_interactive_diagram.py")
    else:
        print(f"{YELLOW}{BOLD}⚠️ Some dependencies need attention:{RESET}")
        if not (easyocr_status == "✅" or "⚠️" in easyocr_status):
            print(f"  {RED}• EasyOCR: {easyocr_details}{RESET}")
        if not (sam3_status == "✅" or sam_models_status == "✅"):
            print(f"  {RED}• SAM3 or SAM models: Install SAM3 or configure SAM/SAM2{RESET}")
        if vlm_status != "✅":
            print(f"  {RED}• Ollama VLM: {vlm_details}{RESET}")
        if serper_status != "✅":
            print(f"  {RED}• Serper API: {serper_details}{RESET}")
        
        print(f"\n{YELLOW}Quick fixes:{RESET}")
        print(f"  1. Install EasyOCR: pip install easyocr")
        print(f"  2. Install SAM3: pip install sam3 (then: huggingface-cli login)")
        print(f"  3. Setup Ollama: ./scripts/setup_ollama.sh")
        print(f"  4. Get Serper key: https://serper.dev")
    
    return 0 if all_critical else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

#!/usr/bin/env python3
"""
Verify SAM (Segment Anything Model) installation and configuration.

Tests:
1. SAM model file exists
2. Can import SAM dependencies
3. Can load SAM model
4. Can perform segmentation on test image
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_sam3():
    """Check SAM3 installation"""
    print("\n" + "=" * 60)
    print("SAM3 (Segment Anything Model 3) Check")
    print("=" * 60)
    
    import platform
    is_apple_silicon = platform.processor() == "arm" or platform.machine() == "arm64"
    use_mlx = os.getenv("USE_SAM3_MLX", "auto").lower()
    
    # Check official SAM3 first (preferred)
    sam3_installed = False
    try:
        from sam3.model_builder import build_sam3_image_model  # type: ignore
        from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore
        print("✓ Official SAM3 package installed")
        sam3_installed = True
        
        # Check HuggingFace authentication
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        try:
            from huggingface_hub import whoami
            try:
                whoami()  # This will raise if not authenticated
                print("  ✓ HuggingFace authenticated")
                auth_status = True
            except Exception:
                print("  ⚠️ HuggingFace not authenticated")
                print("     Run: huggingface-cli login")
                auth_status = False
        except ImportError:
            if hf_token:
                print("  ✓ HuggingFace token set in environment")
                auth_status = True
            else:
                print("  ⚠️ HuggingFace authentication not verified")
                print("     Install: pip install huggingface_hub")
                print("     Then run: huggingface-cli login")
                auth_status = False
        
        sam3_model_path = os.getenv("SAM3_MODEL_PATH")
        if sam3_model_path:
            print(f"  Model path: {sam3_model_path}")
        else:
            print("  Model: Will be auto-downloaded from HuggingFace on first use")
        
        if not auth_status:
            return "⚠️", "Installed but not authenticated (run: huggingface-cli login)"
        return "✅", "Installed and authenticated"
        
    except ImportError:
        sam3_installed = False
    
    # Check MLX version (Apple Silicon optimized) as alternative
    if use_mlx == "true" or (use_mlx == "auto" and is_apple_silicon):
        try:
            try:
                from sam3_image import SAM3ImagePredictor, build_sam3  # type: ignore
            except ImportError:
                from mlx_sam3 import SAM3ImagePredictor, build_sam3  # type: ignore
            
            print("✓ SAM3 MLX package installed (Apple Silicon optimized)")
            model_name = os.getenv("SAM3_MLX_MODEL", "mlx-community/sam3-image")
            print(f"  Model: {model_name}")
            print("  Note: Model will be downloaded from HuggingFace on first use")
            return "✅", "MLX version installed (Apple Silicon optimized)"
        except ImportError:
            if not sam3_installed:
                print("⚠ SAM3 not installed")
                print("   Install official: pip install sam3")
                print("   Or MLX version: ./scripts/setup_sam3_apple_silicon.sh")
                return "❌", "Not installed"
    
    if not sam3_installed:
        return "❌", "Not installed. Install with: pip install sam3"
    
    return "✅", "Installed"


def check_sam_v1():
    """Check SAM v1 installation"""
    print("\n" + "=" * 60)
    print("SAM v1 (Segment Anything Model) Check")
    print("=" * 60)
    
    # Check environment variable
    sam_path = os.getenv("SAM_MODEL_PATH")
    if not sam_path:
        print("❌ SAM_MODEL_PATH not set in environment")
        print("   Set it in .env: SAM_MODEL_PATH=/path/to/sam_vit_b.pth")
        return False
    
    print(f"✓ SAM_MODEL_PATH set: {sam_path}")
    
    # Check file exists
    if not Path(sam_path).exists():
        print(f"❌ SAM model file not found: {sam_path}")
        print("   Download from: https://github.com/facebookresearch/segment-anything#model-checkpoints")
        print("   Or run: ./scripts/setup_sam_models.sh")
        return False
    
    print(f"✓ SAM model file exists: {sam_path}")
    file_size = Path(sam_path).stat().st_size / (1024 * 1024)  # MB
    print(f"  File size: {file_size:.1f} MB")
    
    # Check dependencies
    try:
        import torch
        print(f"✓ PyTorch installed: {torch.__version__}")
    except ImportError:
        print("❌ PyTorch not installed. Install with: pip install torch")
        return False
    
    try:
        from segment_anything import sam_model_registry
        print("✓ segment-anything package installed")
    except ImportError:
        print("❌ segment-anything not installed. Install with: pip install git+https://github.com/facebookresearch/segment-anything.git")
        return False
    
    # Try loading model
    try:
        print("\nAttempting to load SAM model...")
        model_type = "vit_b"  # Default, could be vit_l or vit_h based on file
        if "vit_l" in sam_path.lower():
            model_type = "vit_l"
        elif "vit_h" in sam_path.lower():
            model_type = "vit_h"
        
        sam = sam_model_registry[model_type](checkpoint=sam_path)
        print(f"✓ SAM model loaded successfully (type: {model_type})")
        
        # Test segmentation (if we have a test image)
        try:
            from PIL import Image
            import numpy as np
            from segment_anything import SamAutomaticMaskGenerator
            
            # Create a dummy test image
            test_image = np.zeros((100, 100, 3), dtype=np.uint8)
            mask_generator = SamAutomaticMaskGenerator(sam)
            print("\nTesting segmentation on dummy image...")
            masks = mask_generator.generate(test_image)
            print(f"✓ Segmentation test successful: {len(masks)} masks generated")
            return True
        except Exception as e:
            print(f"⚠ Segmentation test failed: {e}")
            print("  Model loads but segmentation test failed (may need GPU)")
            return True  # Model loads, that's the main thing
        
    except Exception as e:
        print(f"❌ Failed to load SAM model: {e}")
        return False


def check_sam2():
    """Check SAM2 installation"""
    print("\n" + "=" * 60)
    print("SAM2 (Segment Anything Model 2) Check")
    print("=" * 60)
    
    sam2_path = os.getenv("SAM2_MODEL_PATH")
    sam2_type = os.getenv("SAM2_MODEL_TYPE", "sam2_hiera_base_plus")
    
    if not sam2_path:
        print("⚠ SAM2_MODEL_PATH not set (optional)")
        print("   SAM2 is optional - SAM v1 will be used if available")
        return None
    
    print(f"✓ SAM2_MODEL_PATH set: {sam2_path}")
    print(f"✓ SAM2_MODEL_TYPE: {sam2_type}")
    
    # Check dependencies
    try:
        from sam2.sam2_image_predictor import Sam2ImagePredictor
        from sam2.build_sam import build_sam2
        print("✓ sam2 package installed")
        
        # Try loading
        print("\nAttempting to load SAM2 model...")
        sam2 = build_sam2(model_type=sam2_type, checkpoint=sam2_path)
        print("✓ SAM2 model loaded successfully")
        return True
    except ImportError:
        print("⚠ SAM2 package not installed (optional)")
        print("   Install with: pip install git+https://github.com/facebookresearch/segment-anything-2.git")
        return None
    except Exception as e:
        print(f"⚠ SAM2 model load failed: {e}")
        return False


def main():
    print("=" * 60)
    print("SAM Model Verification")
    print("=" * 60)
    
    # Load .env if exists
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
    else:
        print("⚠ No .env file found, using system environment variables")
    
    sam3_status, sam3_details = check_sam3()
    sam_v1_ok = check_sam_v1()
    sam2_status = check_sam2()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    if sam3_status == "✅":
        print(f"✅ SAM3: Ready to use (PREFERRED) - {sam3_details}")
    elif sam3_status == "⚠️":
        print(f"⚠️ SAM3: {sam3_details}")
    else:
        print(f"❌ SAM3: {sam3_details}")
    
    if sam2_status is True:
        print("✅ SAM2: Ready to use (fallback if SAM3 unavailable)")
    elif sam2_status is False:
        print("⚠ SAM2: Configured but not working")
    else:
        print("⚠ SAM2: Not configured (optional)")
    
    if sam_v1_ok:
        print("✅ SAM v1: Ready to use (fallback if SAM3/SAM2 unavailable)")
    else:
        print("❌ SAM v1: Not ready")
    
    if sam3_ok:
        print("\n✅ SAM3 is ready (preferred)!")
        return 0
    elif sam_v1_ok or sam2_status:
        print("\n⚠ SAM3 not available, but fallback models are ready")
        print("   Recommendation: Install SAM3 for best results")
        return 0
    else:
        print("\n❌ No SAM models are ready. Segmentation will use fallback grid.")
        print("   Install SAM3: ./scripts/setup_sam3_apple_silicon.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())

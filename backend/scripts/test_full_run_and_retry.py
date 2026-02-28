#!/usr/bin/env python3
"""Test full pipeline run and retry functionality"""
import requests
import time
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not running: {e}")
        return False

def start_generation(question_text: str):
    """Start a new generation pipeline"""
    print(f"\n🚀 Starting generation for: {question_text}")
    
    url = f"{API_BASE}/generate"
    params = {"question_text": question_text}
    
    try:
        response = requests.post(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        process_id = data.get("process_id")
        run_id = data.get("run_id")
        
        print(f"✅ Generation started")
        print(f"   Process ID: {process_id}")
        print(f"   Run ID: {run_id}")
        
        return process_id, run_id
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start generation: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None, None

def get_run_status(run_id: str):
    """Get status of a pipeline run"""
    url = f"{API_BASE}/observability/runs/{run_id}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get run status: {e}")
        return None

def get_run_stages(run_id: str):
    """Get stages of a pipeline run"""
    url = f"{API_BASE}/observability/runs/{run_id}/stages"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        # API returns {"stages": [...]}, extract the list
        return data.get("stages", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get run stages: {e}")
        return []

def wait_for_completion(run_id: str, timeout: int = 300, poll_interval: int = 5):
    """Wait for pipeline run to complete or fail"""
    print(f"\n⏳ Waiting for pipeline to complete (timeout: {timeout}s)...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout:
        run_data = get_run_status(run_id)
        if not run_data:
            time.sleep(poll_interval)
            continue
        
        status = run_data.get("status")
        
        # Print status if it changed
        if status != last_status:
            print(f"   Status: {status}")
            last_status = status
        
        if status in ["completed", "failed"]:
            elapsed = time.time() - start_time
            print(f"\n✅ Pipeline finished with status: {status} (took {elapsed:.1f}s)")
            return run_data
        
        time.sleep(poll_interval)
    
    print(f"\n⏰ Timeout after {timeout}s")
    return get_run_status(run_id)

def find_failed_stage(run_id: str) -> Optional[str]:
    """Find the first failed stage in a run"""
    stages = get_run_stages(run_id)
    if not stages:
        return None
    
    for stage in stages:
        if stage.get("status") == "failed":
            return stage.get("stage_name")
    
    return None

def retry_from_stage(run_id: str, from_stage: str):
    """Retry pipeline from a specific stage"""
    print(f"\n🔄 Retrying from stage: {from_stage}")
    
    url = f"{API_BASE}/observability/runs/{run_id}/retry"
    payload = {"from_stage": from_stage}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        # Handle 200 OK response
        if response.status_code == 200:
            data = response.json()
            # API returns "new_run_id" not "run_id"
            new_run_id = data.get("new_run_id") or data.get("run_id")
            print(f"✅ Retry started")
            print(f"   New Run ID: {new_run_id}")
            return new_run_id
        
        # Handle 400 Bad Request - might be "already in progress"
        if response.status_code == 400:
            data = response.json()
            detail = data.get("detail", "")
            if "already in progress" in detail.lower():
                # Extract run_id from the detail message
                import re
                match = re.search(r'run ([a-f0-9-]+)', detail)
                if match:
                    existing_run_id = match.group(1)
                    print(f"⚠️  Retry already in progress")
                    print(f"   Existing Run ID: {existing_run_id}")
                    return existing_run_id
                print(f"⚠️  Retry already in progress: {detail}")
                return None
            else:
                print(f"❌ Retry failed: {detail}")
                return None
        
        response.raise_for_status()
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start retry: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return None

def print_stage_summary(run_id: str):
    """Print summary of all stages"""
    stages = get_run_stages(run_id)
    if not stages:
        print("   No stages found")
        return
    
    print(f"\n📊 Stage Summary:")
    for stage in stages:
        # Handle both dict and string formats
        if isinstance(stage, dict):
            name = stage.get("stage_name", "unknown")
            status = stage.get("status", "unknown")
            duration = stage.get("duration_ms")
            error = stage.get("error_message")
        else:
            # Fallback for unexpected format
            name = str(stage)
            status = "unknown"
            duration = None
            error = None
        
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "⏳",
            "pending": "⏸️"
        }.get(status, "❓")
        
        duration_str = f" ({duration}ms)" if duration else ""
        error_str = f" - {error[:50]}..." if error else ""
        print(f"   {status_emoji} {name}: {status}{duration_str}{error_str}")

def main():
    """Main test function"""
    print("=" * 60)
    print("Full Pipeline Run and Retry Test")
    print("=" * 60)
    
    # Check server
    if not check_server():
        print("\n❌ Server is not running. Please start it first:")
        print("   cd backend && source venv/bin/activate")
        print("   PYTHONPATH=. uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    
    # Test question that will trigger label diagram pipeline (SAM segmenter will likely fail)
    question_text = "Label the parts of a plant cell diagram showing nucleus, mitochondria, and cell membrane"
    
    # Step 1: Start full pipeline run
    process_id, run_id = start_generation(question_text)
    if not run_id:
        print("\n❌ Failed to start generation")
        sys.exit(1)
    
    # Step 2: Wait for completion
    final_run_data = wait_for_completion(run_id, timeout=600)  # 10 minute timeout
    
    if not final_run_data:
        print("\n❌ Could not get final run status")
        sys.exit(1)
    
    # Step 3: Print stage summary
    print_stage_summary(run_id)
    
    # Step 4: Find failed stage (should be diagram_image_segmenter)
    failed_stage = find_failed_stage(run_id)
    
    if not failed_stage:
        print("\n⚠️  No failed stage found. Pipeline may have completed successfully.")
        print("   This is unexpected - SAM segmenter should fail without proper setup.")
        print("   Checking if we can still test retry from diagram_image_segmenter...")
        failed_stage = "diagram_image_segmenter"
    
    print(f"\n🎯 Target stage for retry: {failed_stage}")
    
    # Step 5: Test retry
    new_run_id = retry_from_stage(run_id, failed_stage)
    
    if not new_run_id:
        print("\n❌ Retry failed")
        sys.exit(1)
    
    # Step 6: Wait for retry to complete
    print(f"\n⏳ Waiting for retry to complete...")
    retry_final_data = wait_for_completion(new_run_id, timeout=600)
    
    if retry_final_data:
        print_stage_summary(new_run_id)
        print(f"\n✅ Retry completed with status: {retry_final_data.get('status')}")
    else:
        print("\n⚠️  Could not get retry final status")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()

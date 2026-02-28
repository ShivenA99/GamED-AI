#!/usr/bin/env python3
"""View logs from the current run - Cross-platform script"""
import os
import sys
import json
from pathlib import Path

def get_current_run():
    """Get the current run directory"""
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    runs_dir = backend_dir / "logs" / "runs"
    
    # Try symlink first (Unix/Mac)
    current_link = runs_dir / "current"
    if current_link.exists() and current_link.is_symlink():
        return runs_dir / current_link.readlink()
    
    # Try text file (Windows fallback)
    current_txt = runs_dir / "current.txt"
    if current_txt.exists():
        run_id = current_txt.read_text().strip()
        return runs_dir / run_id
    
    return None

def main():
    """Main function"""
    run_dir = get_current_run()
    
    if not run_dir or not run_dir.exists():
        print("No current run found. Start the application first.")
        sys.exit(1)
    
    print(f"Current run: {run_dir.name}")
    print(f"Run directory: {run_dir}")
    print()
    
    # Show metadata
    metadata_file = run_dir / "metadata.json"
    if metadata_file.exists():
        print("=== Run Metadata ===")
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(json.dumps(metadata, indent=2))
        print()
    
    # Show log files
    print("=== Log Files ===")
    log_files = list(run_dir.glob("*.log"))
    if log_files:
        for log_file in sorted(log_files):
            size = log_file.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"  {log_file.name}: {size_mb:.2f} MB")
    else:
        print("  No log files found")
    print()
    
    # Tail the main log
    main_log = run_dir / "main.log"
    if main_log.exists():
        print("=== Tailing main.log (Ctrl+C to exit) ===")
        try:
            with open(main_log, 'r', encoding='utf-8') as f:
                # Go to end of file
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        print(line, end='')
                    else:
                        import time
                        time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nExiting...")
    else:
        print("main.log not found")

if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""Check retry run logs from database"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.models import ExecutionLog

def check_logs(run_id: str):
    db = SessionLocal()
    try:
        logs = db.query(ExecutionLog).filter(
            ExecutionLog.run_id == run_id
        ).order_by(ExecutionLog.timestamp.desc()).limit(20).all()
        
        print(f"Logs for run {run_id}:")
        print("=" * 70)
        for log in logs:
            print(f"[{log.level.upper()}] {log.message}")
            if "checkpoint" in log.message.lower():
                print("  ⭐ CHECKPOINT-RELATED LOG")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    run_id = sys.argv[1] if len(sys.argv) > 1 else "6cfc9805-0543-46ed-80fd-d1c96bd7f74d"
    check_logs(run_id)

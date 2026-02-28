import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class CheckpointStore:
    """Handle checkpointing for pipeline resume."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the checkpoint database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    asset_type TEXT,
                    state TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
    
    def save_checkpoint(self, checkpoint_id: str, job_id: str, asset_type: str, state: Dict[str, Any]) -> None:
        """Save a checkpoint."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO checkpoints
                (id, job_id, asset_type, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                checkpoint_id,
                job_id,
                asset_type,
                json.dumps(state),
                now,
                now
            ))
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT state FROM checkpoints WHERE id = ?',
                (checkpoint_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row[0])
            return None
    
    def find_latest_checkpoint(self, job_id: str) -> Optional[str]:
        """Find the latest checkpoint for a job."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id FROM checkpoints
                WHERE job_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            ''', (job_id,))
            
            row = cursor.fetchone()
            return row[0] if row else None
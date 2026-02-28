"""Migration script to add blueprint_id column to visualizations table"""
from sqlalchemy import text
from app.db.database import engine
from app.utils.logger import setup_logger

logger = setup_logger("migration")

def migrate():
    """Add blueprint_id column to visualizations table if it doesn't exist"""
    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(visualizations)"))
            columns = [row[1] for row in result]
            
            if 'blueprint_id' in columns:
                logger.info("Column blueprint_id already exists in visualizations table")
                return
            
            # Add the column
            logger.info("Adding blueprint_id column to visualizations table...")
            conn.execute(text("""
                ALTER TABLE visualizations 
                ADD COLUMN blueprint_id TEXT
            """))
            conn.commit()
            logger.info("Successfully added blueprint_id column to visualizations table")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    migrate()


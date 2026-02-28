"""Upload route - refactored to use database"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.document_parser import DocumentParser
from app.repositories.question_repository import QuestionRepository
from app.db.session import get_db
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger("upload")

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and parse a document containing a question"""
    logger.info(f"File upload request received - Filename: {file.filename}, Content-Type: {file.content_type}")
    
    try:
        # Read file content
        file_content = await file.read()
        logger.info(f"File read successfully - Size: {len(file_content)} bytes")
        
        # Parse document
        logger.info(f"Parsing document: {file.filename}")
        parser = DocumentParser()
        question_data = parser.parse(file_content, file.filename)
        logger.info(f"Document parsed successfully - Type: {question_data.get('file_type')}, Question length: {len(question_data.get('text', ''))}")
        logger.debug(f"Extracted question: {question_data.get('text', '')[:200]}...")
        logger.debug(f"Extracted options: {question_data.get('options', [])}")
        
        # Store question in database
        question = QuestionRepository.create(db, {
            "text": question_data["text"],
            "options": question_data.get("options"),
            "file_type": question_data.get("file_type"),
            "full_text": question_data.get("full_text", question_data["text"])
        })
        
        logger.info(f"Question stored successfully - ID: {question.id}")
        
        return {
            "question_id": question.id,
            "text": question.text,
            "options": question.options,
            "message": "File uploaded and parsed successfully"
        }
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

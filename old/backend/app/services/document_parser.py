import PyPDF2
from docx import Document
from typing import Dict, List, Any
import re
from io import BytesIO
from app.utils.logger import setup_logger

# Set up logging
logger = setup_logger("document_parser")

class DocumentParser:
    @staticmethod
    def parse_pdf(file_content: bytes) -> Dict[str, any]:
        """Extract text from PDF file"""
        logger.info(f"Parsing PDF - Size: {len(file_content)} bytes")
        try:
            pdf_reader = PyPDF2.PdfReader(file_content)
            logger.debug(f"PDF has {len(pdf_reader.pages)} pages")
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                logger.debug(f"Page {i+1} extracted - {len(page_text)} chars")
            logger.info(f"PDF parsing successful - Total text length: {len(text)} chars")
            return {"text": text, "type": "pdf"}
        except Exception as e:
            logger.error(f"PDF parsing failed: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_docx(file_content: bytes) -> Dict[str, any]:
        """Extract text from DOCX file"""
        logger.info(f"Parsing DOCX - Size: {len(file_content)} bytes")
        try:
            from io import BytesIO
            doc = Document(BytesIO(file_content))
            paragraphs = [paragraph.text for paragraph in doc.paragraphs]
            text = "\n".join(paragraphs)
            logger.info(f"DOCX parsing successful - Paragraphs: {len(paragraphs)}, Total text length: {len(text)} chars")
            return {"text": text, "type": "docx"}
        except Exception as e:
            logger.error(f"DOCX parsing failed: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse DOCX: {str(e)}")

    @staticmethod
    def parse_txt(file_content: bytes) -> Dict[str, any]:
        """Extract text from TXT file"""
        logger.info(f"Parsing TXT - Size: {len(file_content)} bytes")
        try:
            text = file_content.decode('utf-8')
            logger.info(f"TXT parsing successful - Text length: {len(text)} chars")
            return {"text": text, "type": "txt"}
        except Exception as e:
            logger.error(f"TXT parsing failed: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse TXT: {str(e)}")

    @staticmethod
    def extract_question(text: str) -> Dict[str, any]:
        """Extract question and options from text"""
        logger.info(f"Extracting question from text - Length: {len(text)} chars")
        
        # Simple regex patterns to find questions
        question_pattern = r'([A-Z][^.!?]*[?])'
        option_pattern = r'([a-d]\)\s*[^\n]+)'
        
        questions = re.findall(question_pattern, text)
        options = re.findall(option_pattern, text, re.IGNORECASE)
        
        logger.debug(f"Found {len(questions)} potential questions, {len(options)} potential options")
        
        # Clean up options
        cleaned_options = []
        for opt in options:
            cleaned = re.sub(r'^[a-d]\)\s*', '', opt, flags=re.IGNORECASE).strip()
            if cleaned:
                cleaned_options.append(cleaned)
        
        # Get the first question or use the whole text
        question_text = questions[0] if questions else text.split('\n')[0]
        
        result = {
            "text": question_text.strip(),
            "options": cleaned_options if cleaned_options else None,
            "full_text": text
        }
        
        logger.info(f"Question extraction complete - Question length: {len(result['text'])}, Options: {len(cleaned_options) if cleaned_options else 0}")
        logger.debug(f"Extracted question: {result['text'][:200]}...")
        
        return result

    @staticmethod
    def parse(file_content: bytes, filename: str) -> Dict[str, any]:
        """Parse document based on file extension"""
        ext = filename.split('.')[-1].lower()
        
        if ext == 'pdf':
            parsed = DocumentParser.parse_pdf(file_content)
        elif ext in ['docx', 'doc']:
            parsed = DocumentParser.parse_docx(file_content)
        elif ext in ['txt', 'md']:
            parsed = DocumentParser.parse_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Extract question from parsed text
        question_data = DocumentParser.extract_question(parsed["text"])
        question_data["file_type"] = parsed["type"]
        
        return question_data


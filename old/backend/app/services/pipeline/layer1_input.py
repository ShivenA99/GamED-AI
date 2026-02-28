"""Layer 1: Input & Document Processing"""
from typing import Dict, Any
from app.services.document_parser import DocumentParser
from app.services.pipeline.validators import InputValidator, ValidationResult
from app.utils.logger import setup_logger

logger = setup_logger("layer1_input")

class DocumentParserService:
    """Enhanced document parsing service"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.validator = InputValidator()
    
    def parse_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse document and return structured data"""
        logger.info(f"Parsing document: {filename}")
        
        try:
            # Parse document
            parsed_data = self.parser.parse(file_content, filename)
            
            # Validate parsed data
            validation_result = self.validator.validate(parsed_data)
            
            if not validation_result.is_valid:
                logger.error(f"Document validation failed: {validation_result.errors}")
                raise ValueError(f"Document validation failed: {', '.join(validation_result.errors)}")
            
            if validation_result.warnings:
                logger.warning(f"Document validation warnings: {validation_result.warnings}")
            
            logger.info(f"Document parsed successfully: {filename}")
            return {
                "success": True,
                "data": parsed_data,
                "validation": validation_result.to_dict()
            }
        except Exception as e:
            logger.error(f"Document parsing failed: {e}", exc_info=True)
            raise

class QuestionExtractorService:
    """Extract questions with validation"""
    
    def __init__(self):
        self.parser = DocumentParser()
        self.validator = InputValidator()
    
    def extract_question(self, text: str, filename: str = None) -> Dict[str, Any]:
        """Extract question from text"""
        logger.info("Extracting question from text")
        
        try:
            # Extract question
            question_data = self.parser.extract_question(text)
            
            # Add file type if provided
            if filename:
                ext = filename.split('.')[-1].lower()
                question_data["file_type"] = ext
            
            # Validate extracted question
            validation_result = self.validator.validate(question_data)
            
            if not validation_result.is_valid:
                logger.error(f"Question extraction validation failed: {validation_result.errors}")
                raise ValueError(f"Question validation failed: {', '.join(validation_result.errors)}")
            
            logger.info(f"Question extracted successfully - Length: {len(question_data.get('text', ''))}")
            return {
                "success": True,
                "data": question_data,
                "validation": validation_result.to_dict()
            }
        except Exception as e:
            logger.error(f"Question extraction failed: {e}", exc_info=True)
            raise

class ContentValidatorService:
    """Validate content structure and format"""
    
    def __init__(self):
        self.validator = InputValidator()
    
    def validate_content(self, content_data: Dict[str, Any]) -> ValidationResult:
        """Validate content structure and format"""
        logger.info("Validating content structure")
        
        validation_result = self.validator.validate(content_data)
        
        if validation_result.is_valid:
            logger.info("Content validation passed")
        else:
            logger.warning(f"Content validation issues: {validation_result.errors}")
        
        return validation_result



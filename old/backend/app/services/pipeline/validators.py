"""Step validation framework for pipeline stages"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from app.utils.logger import setup_logger
from app.services.template_registry import get_registry

logger = setup_logger("validators")

class ValidationResult:
    """Result of a validation check"""
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }

class StepValidator(ABC):
    """Base class for step validators"""
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate the data for this step"""
        pass

class InputValidator(StepValidator):
    """Validate document input"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate input document data"""
        errors = []
        warnings = []
        
        # Check required fields
        if "text" not in data or not data["text"]:
            errors.append("Question text is required")
        
        if "file_type" not in data:
            warnings.append("File type not specified")
        
        # Validate text length
        if "text" in data:
            text = data["text"]
            if len(text) < 10:
                errors.append("Question text is too short (minimum 10 characters)")
            if len(text) > 10000:
                warnings.append("Question text is very long (over 10,000 characters)")
        
        # Validate options if present
        if "options" in data and data["options"]:
            if not isinstance(data["options"], list):
                errors.append("Options must be a list")
            elif len(data["options"]) < 2:
                warnings.append("Question has fewer than 2 options")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class AnalysisValidator(StepValidator):
    """Validate question analysis results"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate analysis data"""
        errors = []
        warnings = []
        
        required_fields = ["question_type", "subject", "difficulty"]
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate question_type
        if "question_type" in data:
            valid_types = ["coding", "math", "science", "reasoning", "application", "word_problem", "code_completion", "fact_recall"]
            if data["question_type"] not in valid_types:
                warnings.append(f"Unknown question type: {data['question_type']}")
        
        # Validate difficulty
        if "difficulty" in data:
            valid_difficulties = ["beginner", "intermediate", "advanced"]
            if data["difficulty"] not in valid_difficulties:
                errors.append(f"Invalid difficulty level: {data['difficulty']}")
        
        # Validate key_concepts
        if "key_concepts" in data:
            if not isinstance(data["key_concepts"], list):
                errors.append("key_concepts must be a list")
            elif len(data["key_concepts"]) == 0:
                warnings.append("No key concepts identified")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class StoryValidator(StepValidator):
    """Validate story data structure"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate story data"""
        errors = []
        warnings = []
        
        # Check required fields
        if "story_title" not in data or not data.get("story_title"):
            errors.append("Missing required field: story_title")
        
        if "story_context" not in data or not data.get("story_context"):
            errors.append("Missing required field: story_context")
        
        # primary_question is optional if question_flow exists
        if "question_flow" not in data or not data.get("question_flow"):
            errors.append("Missing required field: question_flow")
        elif not data.get("primary_question"):
            warnings.append("primary_question is missing but question_flow exists")
        
        # Validate question_flow
        if "question_flow" in data:
            if not isinstance(data["question_flow"], list):
                errors.append("question_flow must be a list")
            elif len(data["question_flow"]) == 0:
                errors.append("question_flow cannot be empty")
            else:
                # Validate each question in flow
                for i, q in enumerate(data["question_flow"]):
                    if not isinstance(q, dict):
                        errors.append(f"Question {i+1} in flow must be a dictionary")
                    else:
                        # Check for question text in various possible field names
                        # Note: The prompt schema uses "intuitive_question" as the field name
                        question_text = (q.get("question_text") or q.get("intuitive_question") or 
                                        q.get("text") or q.get("question") or q.get("content"))
                        if not question_text:
                            errors.append(f"Question {i+1} missing question text (expected: intuitive_question, question_text, text, question, or content)")
                        elif "answer_structure" not in q:
                            warnings.append(f"Question {i+1} missing answer_structure")
        
        # Validate story_title length
        if "story_title" in data and len(data["story_title"]) > 500:
            warnings.append("Story title is very long (over 500 characters)")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class HTMLValidator(StepValidator):
    """Validate HTML output"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate HTML content"""
        errors = []
        warnings = []
        
        if "html" not in data or not data["html"]:
            errors.append("HTML content is required")
        else:
            html = data["html"]
            
            # Basic HTML structure checks
            if len(html) < 100:
                errors.append("HTML content is too short")
            
            if len(html) > 1000000:  # 1MB limit
                errors.append("HTML content exceeds size limit (1MB)")
            
            # Check for basic HTML tags
            if "<html" not in html.lower() and "<!doctype" not in html.lower():
                warnings.append("HTML may not have proper document structure")
            
            # Check for script tags (security concern)
            if "<script" in html.lower():
                warnings.append("HTML contains script tags - ensure they are safe")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class BlueprintValidator(StepValidator):
    """Validate game blueprint structure"""
    
    def __init__(self):
        self.template_registry = get_registry()
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate blueprint data"""
        errors = []
        warnings = []
        
        # Check for templateType
        if "templateType" not in data:
            errors.append("Missing required field: templateType")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        template_type = data["templateType"]
        
        # Validate template type exists
        if template_type not in self.template_registry.get_template_types():
            errors.append(f"Invalid template type: {template_type}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Get template metadata
        template_metadata = self.template_registry.get_template(template_type)
        if not template_metadata:
            errors.append(f"Template metadata not found for: {template_type}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Validate against template schema
        is_valid, schema_errors = self.template_registry.validate_blueprint(data, template_type)
        if not is_valid:
            errors.extend(schema_errors)
        
        # Additional validation checks
        if "title" not in data or not data.get("title"):
            errors.append("Missing required field: title")
        
        if "narrativeIntro" not in data or not data.get("narrativeIntro"):
            warnings.append("Missing narrativeIntro field")
        
        if "tasks" not in data or not isinstance(data.get("tasks"), list):
            errors.append("Missing or invalid tasks field")
        elif len(data.get("tasks", [])) == 0:
            warnings.append("No tasks defined in blueprint")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

def get_validator(step_name: str) -> Optional[StepValidator]:
    """Get validator for a specific step"""
    validators = {
        "document_parsing": InputValidator(),
        "question_extraction": InputValidator(),
        "question_analysis": AnalysisValidator(),
        "template_routing": None,  # Template routing validation handled internally
        "story_generation": StoryValidator(),
        "blueprint_generation": BlueprintValidator(),
        "asset_planning": None,  # Asset planning validation handled internally
        "asset_generation": None,  # Asset generation validation handled internally
        "html_generation": HTMLValidator(),  # Keep for backward compatibility
    }
    return validators.get(step_name)


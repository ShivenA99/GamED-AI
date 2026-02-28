"""Layer 2: Intent Recognition & Classification"""
from typing import Dict, Any, List
from app.services.llm_service import LLMService
from app.services.pipeline.validators import AnalysisValidator, ValidationResult
from app.utils.logger import setup_logger
import json

logger = setup_logger("layer2_classification")

class QuestionTypeClassifier:
    """Classify question types"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def classify(self, question_text: str, options: List[str] = None) -> Dict[str, Any]:
        """Classify question type"""
        logger.info("Classifying question type")
        
        prompt = f"""Analyze the following question and determine its type. 
        Question types: coding, math, science, reasoning, application, word_problem, code_completion, fact_recall
        
        Question: {question_text}
        Options: {options if options else "None"}
        
        Respond with ONLY a JSON object: {{"question_type": "type_here"}}"""
        
        messages = [
            {"role": "system", "content": "You are a question classification expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Question classified as: {result.get('question_type')}")
            return result
        except Exception as e:
            logger.error(f"Question classification failed: {e}", exc_info=True)
            raise

class SubjectIdentifier:
    """Identify subject and topic"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def identify(self, question_text: str, question_type: str = None) -> Dict[str, Any]:
        """Identify subject and topic"""
        logger.info("Identifying subject and topic")
        
        prompt = f"""Analyze the following question and identify the subject area and specific topic.
        
        Question: {question_text}
        Question Type: {question_type or "unknown"}
        
        Respond with ONLY a JSON object: {{"subject": "subject_here", "topic": "specific_topic_here"}}"""
        
        messages = [
            {"role": "system", "content": "You are an educational content expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Subject identified: {result.get('subject')}, Topic: {result.get('topic')}")
            return result
        except Exception as e:
            logger.error(f"Subject identification failed: {e}", exc_info=True)
            raise

class ComplexityAnalyzer:
    """Analyze question complexity/difficulty"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def analyze(self, question_text: str, question_type: str = None, subject: str = None) -> Dict[str, Any]:
        """Analyze question complexity"""
        logger.info("Analyzing question complexity")
        
        prompt = f"""Analyze the complexity of the following question and determine its difficulty level.
        Difficulty levels: beginner, intermediate, advanced
        
        Question: {question_text}
        Question Type: {question_type or "unknown"}
        Subject: {subject or "unknown"}
        
        Respond with ONLY a JSON object: {{"difficulty": "beginner|intermediate|advanced", "complexity_score": 1-10}}"""
        
        messages = [
            {"role": "system", "content": "You are an educational assessment expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Complexity analyzed - Difficulty: {result.get('difficulty')}, Score: {result.get('complexity_score')}")
            return result
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}", exc_info=True)
            raise

class KeywordExtractor:
    """Extract key concepts and keywords"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def extract(self, question_text: str, subject: str = None) -> Dict[str, Any]:
        """Extract key concepts and keywords"""
        logger.info("Extracting key concepts and keywords")
        
        prompt = f"""Extract the key concepts, keywords, and learning points from the following question.
        
        Question: {question_text}
        Subject: {subject or "unknown"}
        
        Respond with ONLY a JSON object: {{"key_concepts": ["concept1", "concept2", ...], "keywords": ["keyword1", "keyword2", ...], "intent": "what this question tests"}}"""
        
        messages = [
            {"role": "system", "content": "You are a content analysis expert. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service.call_llm(messages, use_anthropic=False)
            
            # Parse JSON response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response)
            logger.info(f"Extracted {len(result.get('key_concepts', []))} key concepts")
            return result
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}", exc_info=True)
            raise

class ClassificationOrchestrator:
    """Orchestrate all classification steps"""
    
    def __init__(self):
        self.type_classifier = QuestionTypeClassifier()
        self.subject_identifier = SubjectIdentifier()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.keyword_extractor = KeywordExtractor()
        self.validator = AnalysisValidator()
    
    def analyze_question(self, question_text: str, options: List[str] = None) -> Dict[str, Any]:
        """Run complete classification pipeline"""
        logger.info("Starting complete question analysis")
        
        try:
            # Step 1: Classify question type
            type_result = self.type_classifier.classify(question_text, options)
            question_type = type_result.get("question_type", "reasoning")
            
            # Step 2: Identify subject
            subject_result = self.subject_identifier.identify(question_text, question_type)
            subject = subject_result.get("subject", "General")
            
            # Step 3: Analyze complexity
            complexity_result = self.complexity_analyzer.analyze(question_text, question_type, subject)
            difficulty = complexity_result.get("difficulty", "intermediate")
            
            # Step 4: Extract keywords
            keyword_result = self.keyword_extractor.extract(question_text, subject)
            key_concepts = keyword_result.get("key_concepts", [])
            intent = keyword_result.get("intent", "")
            
            # Combine results
            analysis = {
                "question_type": question_type,
                "subject": subject,
                "difficulty": difficulty,
                "key_concepts": key_concepts,
                "intent": intent,
                "complexity_score": complexity_result.get("complexity_score"),
                "topic": subject_result.get("topic")
            }
            
            # Validate analysis
            validation_result = self.validator.validate(analysis)
            
            if not validation_result.is_valid:
                logger.error(f"Analysis validation failed: {validation_result.errors}")
                raise ValueError(f"Analysis validation failed: {', '.join(validation_result.errors)}")
            
            logger.info(f"Question analysis complete - Type: {question_type}, Subject: {subject}, Difficulty: {difficulty}")
            
            return {
                "success": True,
                "data": analysis,
                "validation": validation_result.to_dict()
            }
        except Exception as e:
            logger.error(f"Question analysis failed: {e}", exc_info=True)
            raise



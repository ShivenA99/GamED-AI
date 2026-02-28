"""Database models for AI Learning Platform"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.db.database import Base

def generate_uuid():
    """Generate UUID string"""
    return str(uuid.uuid4())

class Question(Base):
    """Question model - stores uploaded questions"""
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # List of options
    file_type = Column(String(50), nullable=True)
    full_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analysis = relationship("QuestionAnalysis", back_populates="question", uselist=False)
    stories = relationship("Story", back_populates="question")
    processes = relationship("Process", back_populates="question")
    blueprints = relationship("GameBlueprint", back_populates="question")

class QuestionAnalysis(Base):
    """Question analysis results"""
    __tablename__ = "question_analyses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, unique=True)
    question_type = Column(String(100), nullable=False)
    subject = Column(String(200), nullable=False)
    difficulty = Column(String(50), nullable=False)  # beginner, intermediate, advanced
    key_concepts = Column(JSON, nullable=True)  # List of concepts
    intent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="analysis")

class Process(Base):
    """Process tracking for pipeline execution"""
    __tablename__ = "processes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, error, cancelled
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(200), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    question = relationship("Question", back_populates="processes")
    steps = relationship("PipelineStep", back_populates="process", order_by="PipelineStep.step_number")
    visualization = relationship("Visualization", back_populates="process", uselist=False)

class Story(Base):
    """Story data generated from questions"""
    __tablename__ = "stories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    story_title = Column(String(500), nullable=False)
    story_context = Column(Text, nullable=False)
    learning_intuition = Column(Text, nullable=True)
    visual_metaphor = Column(Text, nullable=True)
    interaction_design = Column(Text, nullable=True)
    visual_elements = Column(JSON, nullable=True)  # List of visual elements
    question_flow = Column(JSON, nullable=False)  # List of question flow items
    primary_question = Column(Text, nullable=False)
    learning_alignment = Column(Text, nullable=True)
    animation_cues = Column(Text, nullable=True)
    question_implementation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="stories")

class Visualization(Base):
    """Generated HTML visualizations"""
    __tablename__ = "visualizations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    process_id = Column(String, ForeignKey("processes.id"), nullable=False, unique=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    html_content = Column(Text, nullable=True)  # Made nullable for blueprint-based visualizations
    story_data_json = Column(JSON, nullable=False)  # Full story data as JSON
    blueprint_id = Column(String, ForeignKey("game_blueprints.id"), nullable=True)  # Optional link to blueprint
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    process = relationship("Process", back_populates="visualization")
    user_sessions = relationship("UserSession", back_populates="visualization")
    blueprint = relationship("GameBlueprint", back_populates="visualization", uselist=False)

class GameBlueprint(Base):
    """Game blueprint JSON for template-based visualizations"""
    __tablename__ = "game_blueprints"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    template_type = Column(String(100), nullable=False)  # e.g., "LABEL_DIAGRAM", "SEQUENCE_BUILDER"
    blueprint_json = Column(JSON, nullable=False)  # Full blueprint JSON matching template schema
    assets_json = Column(JSON, nullable=True)  # Asset URL map: {"diagram": "url", ...}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="blueprints")
    visualization = relationship("Visualization", back_populates="blueprint", uselist=False)

class UserSession(Base):
    """User session tracking for game plays"""
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    visualization_id = Column(String, ForeignKey("visualizations.id"), nullable=False)
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    answers_json = Column(JSON, nullable=True)  # List of answer records
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    visualization = relationship("Visualization", back_populates="user_sessions")

class PipelineStep(Base):
    """Individual pipeline step tracking"""
    __tablename__ = "pipeline_steps"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    process_id = Column(String, ForeignKey("processes.id"), nullable=False)
    step_name = Column(String(200), nullable=False)  # e.g., "document_parsing", "question_analysis"
    step_number = Column(Integer, nullable=False)  # Order in pipeline
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, completed, error, skipped
    input_data = Column(JSON, nullable=True)  # Sanitized input data
    output_data = Column(JSON, nullable=True)  # Sanitized output data
    error_message = Column(Text, nullable=True)
    validation_result = Column(JSON, nullable=True)  # Validation results
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    process = relationship("Process", back_populates="steps")


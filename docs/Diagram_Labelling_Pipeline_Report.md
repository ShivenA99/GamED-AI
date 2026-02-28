# Diagram Labelling Game Generation Pipeline Report

## Overview

This report provides a comprehensive analysis of the diagram labelling game generation pipeline in the GamED.AI v2 platform. The system uses a multi-agent LangGraph architecture to automatically generate interactive educational games focused on diagram labelling tasks.

## Functional Details

### System Purpose
GamED.AI v2 is an AI-powered educational game generation platform that creates interactive learning experiences. The diagram labelling pipeline specifically generates games where learners drag labels to correct positions on visual diagrams, ideal for teaching anatomy, geography, technical diagrams, and scientific concepts.

### Core Components
- **Backend**: FastAPI-based API with SQLAlchemy database integration
- **Frontend**: Next.js React application with interactive game players
- **Agent System**: 14+ specialized agents using LangGraph orchestration
- **Model Support**: Plug-and-play configuration with OpenAI, Anthropic, Groq (free tier available)
- **Templates**: 18 game templates, with LABEL_DIAGRAM being the most complex

## Current Performance Status

### Strengths
- **Automated Pipeline**: Fully automated from question input to playable game
- **Quality Assurance**: Multi-level validation (schema, semantic, pedagogical) with retry logic
- **Human-in-the-Loop**: Escalation to human review for low-confidence decisions (<0.7 confidence)
- **Fault Tolerance**: Checkpointing system for pipeline recovery and retry capabilities
- **Model Flexibility**: Free tier support via Groq (14,400 requests/day)

### Known Issues and Limitations
- **Image Segmentation**: Relies on SAM3 model; no fallback for older SAM versions
- **VLM Dependency**: Requires Ollama + LLaVA for zone labelling
- **Web Search**: Depends on Serper API for diagram retrieval
- **Retry Logic**: Complex validation loops may cause delays
- **Resource Intensive**: Multiple AI model calls per game generation

### Performance Metrics (Based on Testing)
- **Success Rate**: High for well-defined educational concepts
- **Generation Time**: 2-5 minutes per game (depending on topology)
- **Validation Coverage**: Schema + semantic + pedagogical checks
- **Retry Rate**: ~20-30% of generations require retries
- **Human Review Rate**: ~10-15% of low-confidence decisions

## Sequence and Graph Timeline

### Pipeline Flow Overview
```
Question Input → Input Enhancement → Domain Knowledge → Template Selection → Game Planning → Scene Generation → Image Pipeline → Blueprint Generation → Validation → SVG Generation → Asset Generation → Output
```

### Detailed Sequence (LABEL_DIAGRAM Template)

1. **InputEnhancer** (0-10s)
   - Extracts Bloom's taxonomy level, subject, difficulty, concepts
   - Model: Configurable (default: claude-sonnet)

2. **DomainKnowledgeRetriever** (10-30s)
   - Web search for canonical labels using Serper API
   - Purpose: Ensure accurate terminology for labelling

3. **Router** (30-40s)
   - Selects LABEL_DIAGRAM template with confidence score
   - Model: claude-haiku
   - Confidence threshold: 0.7 (below triggers human review)

4. **GamePlanner** (40-60s)
   - Generates game mechanics, scoring rubric, difficulty levels
   - Model: gpt-4-turbo

5. **SceneGenerator** (60-90s)
   - Plans visual design, layout, and interaction requirements
   - Model: claude-sonnet

6. **DiagramImageRetriever** (90-120s)
   - Searches for relevant diagram images online
   - Technology: Serper Images API

7. **ImageLabelRemover** (120-150s)
   - Removes existing text labels from images using inpainting
   - Purpose: Prepare clean diagram for segmentation

8. **Sam3PromptGenerator** (150-160s)
   - Generates optimized prompts for SAM3 segmentation

9. **DiagramImageSegmenter** (160-200s)
   - Segments image into distinct zones using SAM3
   - Technology: SAM3 model (no fallback to older versions)

10. **DiagramZoneLabeler** (200-250s)
    - Identifies labels for each segmented zone
    - Technology: VLM (Ollama + LLaVA)
    - Can retry image retrieval if labelling fails

11. **BlueprintGenerator** (250-300s)
    - Produces complete JSON blueprint with zones, labels, interactions
    - Model: gpt-4o

12. **BlueprintValidator** (300-320s)
    - Validates blueprint (schema, semantic, pedagogical)
    - Retry loop: max 3 attempts

13. **DiagramSpecGenerator** (320-350s)
    - Generates SVG specification from blueprint
    - Uses LLM + Pydantic schema validation

14. **DiagramSpecValidator** (350-360s)
    - Validates SVG spec before rendering
    - Retry loop: max 3 attempts

15. **DiagramSvgGenerator** (360-380s)
    - Renders interactive SVG from specification

16. **AssetGenerator** (380-420s)
    - Generates additional images/audio assets
    - Final output: Complete playable game

### Topology Configurations
- **T0**: Sequential (no validation) - Fastest, lowest quality
- **T1**: Sequential + Validators - Production default
- **T2**: Actor-Critic - Quality-critical tasks
- **T4**: Self-Refine - Iterative improvement
- **T5**: Multi-Agent Debate - Diverse perspectives
- **T7**: Reflection + Memory - Learning from failures

## Agents Used and Rationale

### Core Agents
1. **InputEnhancer** (claude-sonnet)
   - **Purpose**: Pedagogical analysis of input questions
   - **Why**: Ensures educational alignment and appropriate difficulty

2. **DomainKnowledgeRetriever** (Web Search)
   - **Purpose**: Gather canonical labels and terminology
   - **Why**: Prevents incorrect labelling due to outdated or incorrect terms

3. **Router** (claude-haiku)
   - **Purpose**: Template selection with confidence scoring
   - **Why**: Routes to most appropriate game type based on content analysis

### Diagram-Specific Agents
4. **DiagramImageRetriever** (Serper API)
   - **Purpose**: Find relevant diagram images online
   - **Why**: Provides visual foundation for labelling tasks

5. **ImageLabelRemover** (Inpainting)
   - **Purpose**: Clean existing labels from images
   - **Why**: Ensures learners create labels themselves, not copy existing ones

6. **DiagramImageSegmenter** (SAM3)
   - **Purpose**: Divide image into clickable zones
   - **Why**: Creates interactive areas for label placement

7. **DiagramZoneLabeler** (VLM - LLaVA)
   - **Purpose**: Identify correct labels for each zone
   - **Why**: Uses vision-language understanding to match zones to concepts

### Generation Agents
8. **GamePlanner** (gpt-4-turbo)
   - **Purpose**: Design game mechanics and scoring
   - **Why**: Creates engaging, educational gameplay structure

9. **SceneGenerator** (claude-sonnet)
   - **Purpose**: Plan visual layout and interactions
   - **Why**: Ensures coherent visual design and user experience

10. **BlueprintGenerator** (gpt-4o)
    - **Purpose**: Create complete game specification
    - **Why**: Structured JSON format for frontend rendering

11. **BlueprintValidator** (claude-haiku)
    - **Purpose**: Quality assurance and error checking
    - **Why**: Prevents broken games from reaching users

12. **DiagramSpecGenerator** (LLM + Schema)
    - **Purpose**: Generate SVG specifications
    - **Why**: Creates scalable, interactive vector graphics

13. **DiagramSvgGenerator** (XML Generation)
    - **Purpose**: Render final SVG assets
    - **Why**: Produces browser-compatible interactive diagrams

14. **AssetGenerator** (AI Generation)
    - **Purpose**: Create additional visual/audio assets
    - **Why**: Enhances game engagement and accessibility

## Templates and Architecture Models

### LABEL_DIAGRAM Template Schema
```typescript
{
    templateType: "LABEL_DIAGRAM",
    title: string,
    narrativeIntro: string,
    diagram: {
        assetPrompt: string,
        zones: Array<{
            id: string,
            label: string,
            x: number, // 0-100 percentage
            y: number,
            radius: number
        }>
    },
    labels: Array<{
        id: string,
        text: string,
        correctZoneId: string
    }>,
    distractorLabels?: Array<{
        id: string,
        text: string,
        explanation: string
    }>,
    tasks: Array<{
        type: "label_diagram" | "identify_function" | "trace_path",
        questionText: string,
        requiredToProceed: boolean
    }>,
    animationCues: {
        labelDrag: string,
        correctPlacement: string,
        incorrectPlacement: string
    },
    hints: Array<{
        zoneId: string,
        hintText: string
    }>,
    feedbackMessages: {
        perfect: string,
        good: string,
        retry: string
    }
}
```

### Architecture Models

#### LangGraph State Machine
- **StateGraph**: Orchestrates agent execution flow
- **MemorySaver**: Enables checkpointing and retry capabilities
- **Conditional Edges**: Handle validation failures and routing decisions

#### Agent Communication
- **Shared State**: All agents read/write to AgentState dictionary
- **Instrumentation**: Performance monitoring and error tracking
- **Validation Layers**: Schema, semantic, and pedagogical checks

#### Model Configuration
- **Presets**: groq_free ($0), cost_optimized, balanced, quality_optimized
- **Per-Agent Override**: Fine-tune models for specific agents
- **Temperature Control**: Adjust creativity vs consistency

## Entire Process and Flow

### Input Processing
1. User submits question text (e.g., "Explain binary search")
2. InputEnhancer analyzes pedagogical context
3. DomainKnowledgeRetriever gathers relevant terminology
4. Router selects LABEL_DIAGRAM template

### Image Pipeline
5. DiagramImageRetriever finds suitable diagram images
6. ImageLabelRemover cleans existing labels
7. Sam3PromptGenerator creates segmentation prompts
8. DiagramImageSegmenter divides image into zones
9. DiagramZoneLabeler assigns labels to zones

### Game Generation
10. GamePlanner designs mechanics and scoring
11. SceneGenerator plans visual layout
12. BlueprintGenerator creates complete specification
13. BlueprintValidator ensures quality (retry if needed)

### Asset Generation
14. DiagramSpecGenerator creates SVG specifications
15. DiagramSpecValidator checks specifications
16. DiagramSvgGenerator renders interactive SVG
17. AssetGenerator creates additional assets

### Output
- **JSON Blueprint**: Complete game specification
- **SVG Assets**: Interactive diagram components
- **Playable Game**: Frontend renders drag-and-drop interface

### Error Handling and Recovery
- **Validation Failures**: Retry loops (max 3 attempts)
- **Low Confidence**: Human review escalation
- **Checkpointing**: Resume from last successful stage
- **Fallbacks**: Grid segmentation if SAM3 fails

### Quality Assurance
- **Schema Validation**: Pydantic models ensure data structure
- **Semantic Validation**: Content accuracy and educational value
- **Pedagogical Validation**: Learning objective alignment
- **Integration Testing**: End-to-end pipeline verification

This comprehensive pipeline transforms educational questions into engaging, interactive diagram labelling games with full automation, quality control, and human oversight capabilities.
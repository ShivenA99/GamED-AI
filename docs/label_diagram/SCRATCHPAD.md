# LABEL_DIAGRAM Development Scratchpad

## Known Failure Modes
| ID | Category | Description | Fix Applied | Status |
|----|----------|-------------|-------------|--------|
| FM-001 | Blueprint Schema | LLM returned scene-style JSON (required_assets/layout_specification) instead of diagram.zones + labels | Add LABEL_DIAGRAM sanitization + validation fallback in blueprint_generator; tighten prompt to forbid scene fields | Fixed |
| FM-002 | Diagram Asset | No diagram asset generated for gameplay | Add diagram_spec_generator + diagram_svg_generator and wire into T0/T1 | Fixed |

## Experiments Log

## Debug Notes

## Quick Reference
- Blueprint validation: `backend/app/agents/blueprint_generator.py:804-827`
- Router config: `backend/app/agents/router.py:73-86`
- Prompt template: `backend/prompts/blueprint_label_diagram.txt`
- Diagram spec prompt: `backend/prompts/diagram_svg_spec_label_diagram.txt`
- Diagram spec agent: `backend/app/agents/diagram_spec_generator.py`
- Diagram SVG agent: `backend/app/agents/diagram_svg_generator.py`
- Frontend component: `frontend/src/components/templates/LabelDiagramGame/`
- Game harness: `frontend/src/app/game/[id]/page.tsx`

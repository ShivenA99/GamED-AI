# LABEL_DIAGRAM Prompt Iterations

## Current Version
- File: `backend/prompts/blueprint_label_diagram.txt`
- Last Updated: Initial implementation

## Change Log

### v1.0 - Initial
- Base prompt with heart anatomy and plant cell examples
- Coordinate system rules (0-100 percentage)
- Cross-reference validation checklist

### v1.1 - Schema Guardrails
- Added explicit rule to forbid scene-style fields (required_assets, layout_specification, animation_sequences, game_mechanics)
- Reinforced “schema-only” output requirement

### v1.2 - Diagram SVG Spec Prompt
- Added diagram SVG spec generator prompt (`diagram_svg_spec_label_diagram.txt`)
- Enforced 1:1 label-to-zone mapping and 0-100 coordinate system

## Planned Improvements
- [ ] Add geography examples (world map, country outlines)
- [ ] Add engineering examples (circuit diagrams, engine parts)
- [ ] Add more explicit coordinate guidance
- [ ] Add common failure mode warnings

## Before/After Examples

### Example 1: TBD
**Problem**:
**Before**:
```
```
**After**:
```
```
**Result**:

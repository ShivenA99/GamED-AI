# LABEL_DIAGRAM Quality Metrics

## Test Results by Iteration

### Iteration 1 - MVP
| Test Question | Topology | Blueprint Valid | Zones Valid | Frontend Renders | Play Complete | Notes |
|--------------|----------|-----------------|-------------|------------------|---------------|-------|
| world_map_5_countries | T0 | Yes | Yes | Not tested | Not tested | Schema sanitized; labels/zones aligned |

## Test Questions

| ID | Question | Expected Zones | Difficulty |
|----|----------|---------------|------------|
| heart_anatomy | Label parts of the human heart | 6-8 zones | intermediate |
| plant_cell | Identify organelles in a plant cell | 6-8 zones | intermediate |
| world_map | Label the seven continents | 7 zones | easy |
| cpu_architecture | Label CPU components (ALU, CU, etc) | 5-6 zones | advanced |

## Validation Pass Rates

| Version | T0 Pass Rate | T1 Pass Rate | Notes |
|---------|--------------|--------------|-------|
| v1.1 | 1/1 | Not tested | LABEL_DIAGRAM sanitization + label/zone alignment |

## Known Issues

| Issue | Severity | Status |
|-------|----------|--------|
| Frontend render not re-verified after schema fixes | Low | Open |
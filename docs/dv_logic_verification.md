# DV Logic Verification: Success Criteria & Constraint Logic

**Date**: February 14, 2026  
**Status**: Complete Verification Framework  
**Goal**: Define programmatic verification for all gamified data visualization experiences  

---

## Success Criteria Framework

For each visualization game type, the system must programmatically verify user understanding through measurable outcomes and behavioral patterns.

### Pattern A: Time-Series Line Chart (Health/Fitness) - "Trend Predictor"

**The "Knowledge Check"**: User demonstrates trend comprehension by predicting next 3-5 data points within ±5-10% of actual values, correctly identifying at least 2 of 3 trend characteristics (direction, seasonality, volatility).

**Constraint Logic**: Loss State occurs when prediction error exceeds 25% for 3 consecutive attempts, or when user fails to identify obvious trend breaks (plateaus, spikes) after 2 hint requests.

### Pattern B: Time-Series Line Chart (Finance/Business) - "Resource Optimizer"

**The "Knowledge Check"**: User achieves target metric (revenue/profit) within ±5-10% while keeping volatility below threshold, demonstrating understanding of parameter interdependencies through successful scenario navigation.

**Constraint Logic**: Loss State triggered by budget exhaustion (allocating >100% of available resources) or failing to meet minimum performance threshold after 3 optimization rounds.

### Pattern C: Time-Series + Scenario Bands (Climate/Civic) - "Policy Simulator"

**The "Knowledge Check"**: User keeps key indicator (temperature, emissions) within safe bounds across 2+ scenarios, correctly predicting trajectory changes when adjusting 3+ policy variables within ±0.1°C or 5% margin.

**Constraint Logic**: Loss State when tipping points are exceeded (e.g., temperature >2°C above baseline) or when user cannot stabilize trajectory after maximum policy adjustments (5 attempts).

### Pattern D: Treemap (File/Portfolio Management) - "Space Rebalancer"

**The "Knowledge Check"**: User achieves target allocation (no category >25% of total) while staying within risk constraints, demonstrating hierarchical understanding by correctly prioritizing high-impact moves.

**Constraint Logic**: Loss State when constraint violations accumulate (>3 size limit breaches or risk threshold exceedances) or when user cannot reach target state within move limit (10 actions).

### Pattern E: Node-Link Network Graphs (Logistics/Networks) - "Flow Optimizer"

**The "Knowledge Check"**: User maintains network connectivity (>95% flow capacity) while identifying and resolving bottlenecks, correctly predicting flow changes after topology modifications.

**Constraint Logic**: Loss State when network becomes disconnected or flow drops below 50% of optimal, or when user exceeds reconnection attempts (3 per disruption event).

### Pattern F: Choropleth/Geo Maps (Civic/Climate) - "Region Strategist"

**The "Knowledge Check"**: User correctly predicts spatial distribution changes by allocating resources to reduce high-risk areas by >30%, demonstrating understanding of geographic interdependencies.

**Constraint Logic**: Loss State when resource budget is depleted without achieving minimum risk reduction (20%), or when spatial patterns worsen after resource allocation.

### Pattern G: Progress Bars & KPI Dashboards - "Goal Balancer"

**The "Knowledge Check"**: User advances all KPIs above minimum thresholds while understanding trade-offs, demonstrated by achieving balanced progress (no KPI <60% of target) through optimal effort allocation.

**Constraint Logic**: Loss State when any KPI falls to critical levels (<20%) or when effort allocation leads to overall performance degradation despite individual gains.

### Pattern H: Visualization-Literacy Card Games - "Chart Chooser"

**The "Knowledge Check"**: User selects appropriate chart types for 80%+ of scenarios, correctly articulating why each choice fits the data characteristics and task requirements.

**Constraint Logic**: Loss State when incorrect chart selections exceed 3 in a round, or when user cannot justify choices with valid data visualization principles.

### Pattern I: "Data Quizzes" (Interactive Journalism) - "Intuition Tester"

**The "Knowledge Check"**: User reduces preconception-reality gap by >50% across multiple attempts, correctly identifying key data patterns (outliers, trends, distributions) within specified margins.

**Constraint Logic**: Loss State when prediction accuracy remains below 25% after 5 attempts, or when user shows no improvement in understanding data patterns.

---

## Constraint Logic Implementation

### Time-Based Constraints
- **Reading Limit**: 10-30 seconds to analyze visualization before input required
- **Decision Deadline**: 60 seconds per major decision (allocation, prediction)
- **Round Time Limit**: 5-10 minutes per complete challenge

### Attempt-Based Constraints
- **Maximum Guesses**: 3-5 attempts per prediction/validation
- **Hint Usage Cap**: 2-3 hints per challenge to prevent over-reliance
- **Reset Limit**: 1-2 full resets per game session

### Performance-Based Constraints
- **Accuracy Threshold**: Minimum 70% correctness for progression
- **Consistency Requirement**: Maintain performance across 3+ rounds
- **Improvement Mandate**: Show learning curve (better performance over time)

### Validation Triggers
- **Real-time Feedback**: Immediate validation after each action
- **Progressive Difficulty**: Constraints tighten as user demonstrates mastery
- **Adaptive Assistance**: Hint availability based on struggle detection

---

## Verification Metrics

### Quantitative Measures
- **Accuracy Score**: Percentage of correct predictions/identifications
- **Efficiency Rating**: Actions required vs. optimal solution path
- **Consistency Index**: Performance stability across attempts
- **Learning Velocity**: Improvement rate over time

### Qualitative Measures
- **Insight Recognition**: Ability to articulate data patterns
- **Strategy Adaptation**: Modification of approach based on feedback
- **Error Pattern Analysis**: Identification of systematic mistakes
- **Reflection Quality**: Post-game analysis of decision rationale

### Mastery Thresholds
- **Novice**: >60% accuracy with hints, basic pattern recognition
- **Intermediate**: >75% accuracy independently, understands interdependencies
- **Expert**: >90% accuracy, can explain complex relationships and trade-offs
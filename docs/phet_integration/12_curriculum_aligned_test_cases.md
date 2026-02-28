# Curriculum-Aligned PhET Test Cases

Real educational questions mapped to PhET simulations, organized by subject and grade level.

---

## Physics - Mechanics

### Grade 9-10: Kinematics

#### Question 1: Projectile Motion Basics
**Original Question:**
> "A ball is thrown horizontally from a cliff 20m high at 15 m/s. Calculate the time to hit the ground and the horizontal distance traveled."

**Simulation:** projectile-motion

**Agent Transformation:**

| Agent | Action |
|-------|--------|
| **Router** | Detects "thrown", "cliff", "distance" → PHET_SIMULATION |
| **Pedagogical Context** | Bloom's: Apply, Topic: 2D Kinematics |
| **Simulation Selector** | projectile-motion (exact match) |
| **Game Planner** | assessment_type: target_achievement |
| **Assessment Designer** | Create verification checkpoints |

**Generated Blueprint Excerpt:**
```json
{
  "title": "Cliff Projectile Challenge",
  "narrativeIntro": "You're a physics detective! A ball was thrown horizontally from a 20m cliff. Use the simulation to verify your calculations.",
  "simulation": {
    "simulationId": "projectile-motion",
    "initialParameters": {
      "initialHeight": 20,
      "initialSpeed": 15,
      "cannonAngle": 0,
      "airResistance": false
    }
  },
  "tasks": [
    {
      "id": "task_setup",
      "title": "Set Up the Scenario",
      "description": "Configure the cannon to match the problem: 20m height, 15 m/s speed, horizontal throw (0°)",
      "checkpoints": [
        {
          "id": "cp_height",
          "condition": { "type": "property_equals", "property": "initialHeight", "value": 20 }
        },
        {
          "id": "cp_speed",
          "condition": { "type": "property_equals", "property": "initialSpeed", "value": 15 }
        },
        {
          "id": "cp_angle",
          "condition": { "type": "property_equals", "property": "cannonAngle", "value": 0 }
        }
      ]
    },
    {
      "id": "task_verify",
      "title": "Verify Your Calculation",
      "description": "Fire the projectile. Does it land where you predicted? (Hint: t ≈ 2.02s, range ≈ 30.3m)",
      "checkpoints": [
        {
          "id": "cp_fired",
          "condition": { "type": "interaction_occurred", "interaction": "projectileFired" }
        },
        {
          "id": "cp_range_correct",
          "condition": { "type": "property_range", "property": "range", "min": 29, "max": 32 }
        }
      ]
    }
  ]
}
```

---

#### Question 2: Maximum Range Problem
**Original Question:**
> "At what angle should a projectile be launched to achieve maximum horizontal range? Prove your answer experimentally."

**Simulation:** projectile-motion

**Assessment Type:** parameter_discovery

**Generated Tasks:**
```json
{
  "tasks": [
    {
      "id": "task_hypothesis",
      "title": "Make a Prediction",
      "description": "Before experimenting, what angle do you think will give the maximum range?",
      "type": "prediction",
      "checkpoints": [
        {
          "id": "cp_prediction_made",
          "condition": { "type": "interaction_occurred", "interaction": "predictionSubmitted" }
        }
      ]
    },
    {
      "id": "task_experiment",
      "title": "Systematic Testing",
      "description": "Test angles from 15° to 75° in 15° increments. Record the range for each.",
      "checkpoints": [
        {
          "id": "cp_tested_15",
          "condition": { "type": "property_range", "property": "cannonAngle", "min": 13, "max": 17 }
        },
        {
          "id": "cp_tested_30",
          "condition": { "type": "property_range", "property": "cannonAngle", "min": 28, "max": 32 }
        },
        {
          "id": "cp_tested_45",
          "condition": { "type": "property_range", "property": "cannonAngle", "min": 43, "max": 47 }
        },
        {
          "id": "cp_tested_60",
          "condition": { "type": "property_range", "property": "cannonAngle", "min": 58, "max": 62 }
        },
        {
          "id": "cp_tested_75",
          "condition": { "type": "property_range", "property": "cannonAngle", "min": 73, "max": 77 }
        }
      ]
    },
    {
      "id": "task_conclusion",
      "title": "Find the Optimal Angle",
      "description": "Set the cannon to the angle that gave maximum range",
      "checkpoints": [
        {
          "id": "cp_optimal_found",
          "condition": { "type": "property_range", "property": "cannonAngle", "min": 44, "max": 46 }
        }
      ]
    }
  ]
}
```

---

### Grade 11-12: Energy Conservation

#### Question 3: Energy Transformation
**Original Question:**
> "A 50 kg skateboarder starts from rest at the top of a 4m high ramp. Assuming no friction, calculate their speed at the bottom using conservation of energy."

**Simulation:** energy-skate-park

**Assessment Type:** prediction_verification

**Generated Blueprint:**
```json
{
  "title": "Energy Conservation Verification",
  "narrativeIntro": "Use conservation of energy: mgh = ½mv². For h=4m, v should equal √(2gh) = √(2×9.8×4) ≈ 8.85 m/s. Verify this with the simulation!",
  "simulation": {
    "simulationId": "energy-skate-park",
    "initialParameters": {
      "friction": 0,
      "skaterMass": 50
    }
  },
  "tasks": [
    {
      "id": "task_predict",
      "title": "Calculate First",
      "description": "Using PE = KE, calculate the expected speed at the bottom (answer: ~8.85 m/s)",
      "checkpoints": [
        {
          "id": "cp_calculation_time",
          "condition": { "type": "time_spent", "minSeconds": 30 }
        }
      ]
    },
    {
      "id": "task_setup",
      "title": "Set Up the Experiment",
      "description": "Position the skater at exactly 4 meters height. Make sure friction is OFF.",
      "checkpoints": [
        {
          "id": "cp_correct_height",
          "condition": { "type": "property_range", "property": "skaterHeight", "min": 3.9, "max": 4.1 }
        },
        {
          "id": "cp_no_friction",
          "condition": { "type": "property_equals", "property": "friction", "value": 0 }
        }
      ]
    },
    {
      "id": "task_verify",
      "title": "Verify Your Answer",
      "description": "Release the skater and observe the speed at the bottom",
      "checkpoints": [
        {
          "id": "cp_speed_verified",
          "condition": { "type": "property_range", "property": "skaterSpeed", "min": 8.5, "max": 9.2 }
        },
        {
          "id": "cp_ke_equals_pe",
          "description": "KE at bottom ≈ PE at top",
          "condition": { "type": "property_range", "property": "kineticEnergy", "min": 1900, "max": 2000 }
        }
      ]
    }
  ]
}
```

---

### Grade 11-12: Newton's Laws

#### Question 4: Friction and Motion
**Original Question:**
> "A 10 kg box sits on a floor with coefficient of friction μ = 0.3. What is the minimum force needed to start moving the box?"

**Simulation:** forces-and-motion-basics

**Assessment Type:** target_achievement

**Generated Blueprint:**
```json
{
  "title": "Overcoming Static Friction",
  "narrativeIntro": "Calculate: F_friction = μ × m × g = 0.3 × 10 × 9.8 = 29.4 N. Find the minimum force to get the box moving!",
  "tasks": [
    {
      "id": "task_find_threshold",
      "title": "Find the Friction Threshold",
      "description": "Gradually increase the applied force until the box just starts to move",
      "checkpoints": [
        {
          "id": "cp_below_threshold",
          "description": "Apply force below threshold - box shouldn't move",
          "condition": { "type": "property_range", "property": "appliedForce", "min": 20, "max": 28 }
        },
        {
          "id": "cp_box_stationary",
          "condition": { "type": "property_equals", "property": "velocity", "value": 0 }
        },
        {
          "id": "cp_threshold_reached",
          "description": "Find the exact threshold force",
          "condition": { "type": "property_range", "property": "appliedForce", "min": 29, "max": 31 }
        },
        {
          "id": "cp_box_moving",
          "condition": { "type": "property_range", "property": "velocity", "min": 0.01, "max": 10 }
        }
      ]
    }
  ]
}
```

---

## Physics - Waves & Oscillations

### Grade 10-11: Simple Harmonic Motion

#### Question 5: Pendulum Period
**Original Question:**
> "A simple pendulum has a period of 2 seconds on Earth. What is its length? Verify using T = 2π√(L/g)"

**Simulation:** pendulum-lab

**Assessment Type:** measurement + target_achievement

**Generated Blueprint:**
```json
{
  "title": "Pendulum Length Investigation",
  "narrativeIntro": "From T = 2π√(L/g), if T = 2s and g = 9.8 m/s², then L = gT²/4π² ≈ 0.99m. Find this length experimentally!",
  "tasks": [
    {
      "id": "task_find_length",
      "title": "Find the Correct Length",
      "description": "Adjust the pendulum length until you get a period of exactly 2 seconds",
      "checkpoints": [
        {
          "id": "cp_use_timer",
          "description": "Use the period timer tool",
          "condition": { "type": "interaction_occurred", "interaction": "periodTimerStarted" }
        },
        {
          "id": "cp_period_achieved",
          "description": "Period is approximately 2 seconds",
          "condition": { "type": "property_range", "property": "measuredPeriod", "min": 1.95, "max": 2.05 }
        },
        {
          "id": "cp_correct_length",
          "description": "Length should be approximately 1 meter",
          "condition": { "type": "property_range", "property": "length", "min": 0.95, "max": 1.05 }
        }
      ]
    },
    {
      "id": "task_verify_independence",
      "title": "Mass Independence Test",
      "description": "Change the mass and verify the period stays the same",
      "checkpoints": [
        {
          "id": "cp_mass_changed",
          "condition": { "type": "exploration_breadth", "property": "mass", "minUniqueValues": 3 }
        },
        {
          "id": "cp_period_unchanged",
          "condition": { "type": "property_range", "property": "measuredPeriod", "min": 1.9, "max": 2.1 }
        }
      ]
    }
  ]
}
```

---

#### Question 6: Wave Properties
**Original Question:**
> "If a wave has a frequency of 2 Hz and wavelength of 0.5 m, what is the wave speed? Demonstrate this relationship."

**Simulation:** wave-on-a-string

**Assessment Type:** parameter_discovery

**Generated Blueprint:**
```json
{
  "title": "Wave Speed Investigation",
  "narrativeIntro": "Wave speed = frequency × wavelength. For f=2Hz and λ=0.5m, v should equal 1 m/s. Explore how changing frequency affects wavelength at constant wave speed.",
  "tasks": [
    {
      "id": "task_set_frequency",
      "title": "Set the Frequency",
      "description": "Set the oscillator frequency to 2 Hz",
      "checkpoints": [
        {
          "id": "cp_frequency_set",
          "condition": { "type": "property_range", "property": "frequency", "min": 1.9, "max": 2.1 }
        }
      ]
    },
    {
      "id": "task_measure_wavelength",
      "title": "Measure Wavelength",
      "description": "Use the ruler to measure the wavelength (distance between crests)",
      "checkpoints": [
        {
          "id": "cp_ruler_used",
          "condition": { "type": "interaction_occurred", "interaction": "rulerEnabled" }
        },
        {
          "id": "cp_wavelength_measured",
          "condition": { "type": "property_range", "property": "wavelength", "min": 0.4, "max": 0.6 }
        }
      ]
    },
    {
      "id": "task_verify_relationship",
      "title": "Verify v = fλ",
      "description": "Double the frequency. What happens to the wavelength?",
      "checkpoints": [
        {
          "id": "cp_frequency_doubled",
          "condition": { "type": "property_range", "property": "frequency", "min": 3.9, "max": 4.1 }
        },
        {
          "id": "cp_wavelength_halved",
          "description": "Wavelength should be approximately halved",
          "condition": { "type": "property_range", "property": "wavelength", "min": 0.2, "max": 0.3 }
        }
      ]
    }
  ]
}
```

---

## Chemistry - States of Matter

### Grade 8-9: Phase Changes

#### Question 7: Melting and Boiling Points
**Original Question:**
> "Water melts at 0°C and boils at 100°C. Observe the molecular behavior at each phase transition and explain what happens to the molecules."

**Simulation:** states-of-matter

**Assessment Type:** exploration

**Generated Blueprint:**
```json
{
  "title": "Phase Transitions of Water",
  "narrativeIntro": "Watch water molecules as they transition from solid ice to liquid water to steam. Pay attention to how the molecules move differently in each phase!",
  "simulation": {
    "simulationId": "states-of-matter",
    "initialParameters": {
      "substance": "water",
      "temperature": 200
    }
  },
  "tasks": [
    {
      "id": "task_solid",
      "title": "Observe Solid Ice",
      "description": "Cool the water below 273K (0°C) to see solid ice. Notice how the molecules vibrate in fixed positions.",
      "checkpoints": [
        {
          "id": "cp_temp_freezing",
          "condition": { "type": "property_range", "property": "temperature", "min": 100, "max": 270 }
        },
        {
          "id": "cp_phase_solid",
          "condition": { "type": "property_equals", "property": "phase", "value": "solid" }
        },
        {
          "id": "cp_observe_solid",
          "condition": { "type": "time_spent", "minSeconds": 15 }
        }
      ]
    },
    {
      "id": "task_melting",
      "title": "Watch Ice Melt",
      "description": "Slowly heat to 273K and watch the phase transition. The molecules start moving more freely!",
      "checkpoints": [
        {
          "id": "cp_at_melting_point",
          "condition": { "type": "property_range", "property": "temperature", "min": 270, "max": 280 }
        },
        {
          "id": "cp_phase_liquid",
          "condition": { "type": "property_equals", "property": "phase", "value": "liquid" }
        }
      ]
    },
    {
      "id": "task_boiling",
      "title": "Boil the Water",
      "description": "Heat to 373K (100°C) and observe boiling. Molecules gain enough energy to escape!",
      "checkpoints": [
        {
          "id": "cp_at_boiling_point",
          "condition": { "type": "property_range", "property": "temperature", "min": 370, "max": 380 }
        },
        {
          "id": "cp_phase_gas",
          "condition": { "type": "property_equals", "property": "phase", "value": "gas" }
        }
      ]
    }
  ]
}
```

---

### Grade 10-11: Gas Laws

#### Question 8: Boyle's Law
**Original Question:**
> "Demonstrate Boyle's Law: At constant temperature, pressure and volume are inversely proportional (P₁V₁ = P₂V₂). If you halve the volume, what happens to pressure?"

**Simulation:** gas-properties

**Assessment Type:** parameter_discovery

**Generated Blueprint:**
```json
{
  "title": "Boyle's Law Investigation",
  "narrativeIntro": "Boyle's Law states PV = constant (at constant T). If you halve V, P should double. Let's verify this!",
  "simulation": {
    "simulationId": "gas-properties",
    "initialParameters": {
      "holdConstant": "temperature",
      "numberOfParticles": 100
    }
  },
  "tasks": [
    {
      "id": "task_record_initial",
      "title": "Record Initial State",
      "description": "Note the initial pressure and volume values",
      "checkpoints": [
        {
          "id": "cp_initial_observed",
          "condition": { "type": "time_spent", "minSeconds": 10 }
        }
      ]
    },
    {
      "id": "task_halve_volume",
      "title": "Halve the Volume",
      "description": "Reduce the container volume to half its original size",
      "checkpoints": [
        {
          "id": "cp_volume_halved",
          "condition": { "type": "property_range", "property": "volumeRatio", "min": 0.45, "max": 0.55 }
        },
        {
          "id": "cp_pressure_doubled",
          "description": "Pressure should approximately double",
          "condition": { "type": "property_range", "property": "pressureRatio", "min": 1.8, "max": 2.2 }
        }
      ]
    },
    {
      "id": "task_verify_pv_constant",
      "title": "Verify P×V = Constant",
      "description": "Try different volumes and verify that P×V stays the same",
      "checkpoints": [
        {
          "id": "cp_multiple_volumes",
          "condition": { "type": "exploration_breadth", "property": "volume", "minUniqueValues": 4 }
        },
        {
          "id": "cp_pv_constant",
          "condition": { "type": "property_range", "property": "pvProduct", "min": 95, "max": 105 }
        }
      ]
    }
  ]
}
```

---

#### Question 9: Charles's Law
**Original Question:**
> "At constant pressure, how does the volume of a gas change with temperature? Graph V vs T and find the relationship."

**Simulation:** gas-properties

**Assessment Type:** parameter_discovery

**Generated Blueprint:**
```json
{
  "title": "Charles's Law Discovery",
  "narrativeIntro": "Charles's Law: V/T = constant (at constant P). As temperature increases, volume increases proportionally.",
  "tasks": [
    {
      "id": "task_constant_pressure",
      "title": "Set Constant Pressure Mode",
      "description": "Configure the simulation to hold pressure constant",
      "checkpoints": [
        {
          "id": "cp_mode_set",
          "condition": { "type": "property_equals", "property": "holdConstant", "value": "pressure" }
        }
      ]
    },
    {
      "id": "task_vary_temperature",
      "title": "Vary Temperature",
      "description": "Test at least 4 different temperatures and observe the volume",
      "checkpoints": [
        {
          "id": "cp_temp_varied",
          "condition": { "type": "exploration_breadth", "property": "temperature", "minUniqueValues": 4 }
        }
      ]
    },
    {
      "id": "task_double_temp",
      "title": "Double the Temperature",
      "description": "If you double absolute temperature, volume should also double",
      "checkpoints": [
        {
          "id": "cp_temp_doubled",
          "condition": { "type": "property_range", "property": "temperatureRatio", "min": 1.9, "max": 2.1 }
        },
        {
          "id": "cp_volume_doubled",
          "condition": { "type": "property_range", "property": "volumeRatio", "min": 1.8, "max": 2.2 }
        }
      ]
    }
  ]
}
```

---

## Physics - Electricity & Magnetism

### Grade 9-10: Basic Circuits

#### Question 10: Ohm's Law
**Original Question:**
> "Using Ohm's Law (V = IR), if a circuit has a 9V battery and a 3Ω resistor, what current flows? Build this circuit to verify."

**Simulation:** circuit-construction-kit-dc

**Assessment Type:** construction + verification

**Generated Blueprint:**
```json
{
  "title": "Ohm's Law Verification",
  "narrativeIntro": "Ohm's Law: V = IR. For V=9V and R=3Ω, current I = V/R = 9/3 = 3A. Build the circuit and verify!",
  "tasks": [
    {
      "id": "task_build_circuit",
      "title": "Build the Circuit",
      "description": "Connect a 9V battery to a 3Ω resistor in a complete circuit",
      "checkpoints": [
        {
          "id": "cp_battery_added",
          "condition": { "type": "property_range", "property": "batteryCount", "min": 1, "max": 5 }
        },
        {
          "id": "cp_resistor_added",
          "condition": { "type": "property_range", "property": "resistorCount", "min": 1, "max": 5 }
        },
        {
          "id": "cp_circuit_complete",
          "description": "Circuit is closed and current flows",
          "condition": { "type": "property_range", "property": "current", "min": 0.1, "max": 50 }
        }
      ]
    },
    {
      "id": "task_set_values",
      "title": "Set Component Values",
      "description": "Set battery to 9V and resistor to 3Ω",
      "checkpoints": [
        {
          "id": "cp_voltage_set",
          "condition": { "type": "property_range", "property": "batteryVoltage", "min": 8.5, "max": 9.5 }
        },
        {
          "id": "cp_resistance_set",
          "condition": { "type": "property_range", "property": "resistance", "min": 2.8, "max": 3.2 }
        }
      ]
    },
    {
      "id": "task_verify_current",
      "title": "Verify the Current",
      "description": "The ammeter should read approximately 3A",
      "checkpoints": [
        {
          "id": "cp_current_correct",
          "condition": { "type": "property_range", "property": "current", "min": 2.8, "max": 3.2 }
        }
      ]
    }
  ]
}
```

---

#### Question 11: Series vs Parallel Circuits
**Original Question:**
> "Compare the brightness of two light bulbs when connected in series vs. parallel to the same battery. Explain your observations."

**Simulation:** circuit-construction-kit-dc

**Assessment Type:** comparative_analysis

**Generated Blueprint:**
```json
{
  "title": "Series vs Parallel Brightness",
  "narrativeIntro": "In series, current is divided and bulbs are dimmer. In parallel, each bulb gets full voltage and maximum brightness. Test both configurations!",
  "tasks": [
    {
      "id": "task_series",
      "title": "Build Series Circuit",
      "description": "Connect two light bulbs in SERIES with one battery. Observe their brightness.",
      "checkpoints": [
        {
          "id": "cp_series_built",
          "condition": { "type": "property_equals", "property": "circuitType", "value": "series" }
        },
        {
          "id": "cp_two_bulbs_series",
          "condition": { "type": "property_equals", "property": "bulbCount", "value": 2 }
        },
        {
          "id": "cp_series_brightness_noted",
          "condition": { "type": "time_spent", "minSeconds": 15 }
        }
      ]
    },
    {
      "id": "task_parallel",
      "title": "Build Parallel Circuit",
      "description": "Now connect the same two bulbs in PARALLEL. Compare brightness to series.",
      "checkpoints": [
        {
          "id": "cp_parallel_built",
          "condition": { "type": "property_equals", "property": "circuitType", "value": "parallel" }
        },
        {
          "id": "cp_brighter_in_parallel",
          "description": "Bulbs should be brighter in parallel",
          "condition": { "type": "property_range", "property": "bulbBrightness", "min": 0.8, "max": 1.0 }
        }
      ]
    }
  ]
}
```

---

### Grade 11-12: Electromagnetism

#### Question 12: Faraday's Law of Induction
**Original Question:**
> "A magnet is moved through a coil of wire. Explain how the induced EMF changes with: (a) speed of magnet, (b) number of coil loops, (c) magnet strength."

**Simulation:** faradays-law

**Assessment Type:** parameter_discovery

**Generated Blueprint:**
```json
{
  "title": "Factors Affecting Induced EMF",
  "narrativeIntro": "Faraday's Law: EMF = -N × dΦ/dt. The induced voltage depends on: rate of flux change (speed), number of loops, and magnetic field strength.",
  "tasks": [
    {
      "id": "task_speed_effect",
      "title": "Effect of Speed",
      "description": "Move the magnet slowly, then quickly. Observe how speed affects the voltmeter reading.",
      "checkpoints": [
        {
          "id": "cp_slow_movement",
          "description": "Move magnet slowly - small voltage",
          "condition": { "type": "property_range", "property": "voltage", "min": 0.1, "max": 2 }
        },
        {
          "id": "cp_fast_movement",
          "description": "Move magnet quickly - larger voltage",
          "condition": { "type": "property_range", "property": "voltage", "min": 5, "max": 20 }
        }
      ]
    },
    {
      "id": "task_loops_effect",
      "title": "Effect of Coil Loops",
      "description": "Change the number of loops in the coil. More loops = more voltage.",
      "checkpoints": [
        {
          "id": "cp_loops_varied",
          "condition": { "type": "exploration_breadth", "property": "numberOfLoops", "minUniqueValues": 3 }
        },
        {
          "id": "cp_more_loops_more_voltage",
          "description": "Doubling loops should approximately double voltage",
          "condition": { "type": "property_range", "property": "voltageRatio", "min": 1.5, "max": 2.5 }
        }
      ]
    }
  ]
}
```

---

## Physics - Gravitation & Orbits

### Grade 11-12: Orbital Mechanics

#### Question 13: Kepler's Laws
**Original Question:**
> "Demonstrate that a planet's orbital period squared is proportional to its orbital radius cubed (T² ∝ r³)."

**Simulation:** gravity-and-orbits

**Assessment Type:** measurement + parameter_discovery

**Generated Blueprint:**
```json
{
  "title": "Kepler's Third Law Investigation",
  "narrativeIntro": "Kepler discovered that T² = (4π²/GM)r³. This means if you double the orbital radius, the period increases by factor of √8 ≈ 2.83.",
  "tasks": [
    {
      "id": "task_measure_period",
      "title": "Measure Orbital Period",
      "description": "At the default orbital distance, time one complete orbit",
      "checkpoints": [
        {
          "id": "cp_one_orbit_timed",
          "condition": { "type": "interaction_occurred", "interaction": "orbitCompleted" }
        }
      ]
    },
    {
      "id": "task_change_distance",
      "title": "Change Orbital Distance",
      "description": "Move the planet to a different orbital distance and measure the new period",
      "checkpoints": [
        {
          "id": "cp_distance_changed",
          "condition": { "type": "property_changed", "property": "orbitalRadius" }
        },
        {
          "id": "cp_new_orbit_timed",
          "condition": { "type": "interaction_occurred", "interaction": "orbitCompleted" }
        }
      ]
    },
    {
      "id": "task_verify_relationship",
      "title": "Verify T² ∝ r³",
      "description": "Calculate T²/r³ for both measurements. They should be equal!",
      "checkpoints": [
        {
          "id": "cp_multiple_measurements",
          "condition": { "type": "exploration_breadth", "property": "orbitalRadius", "minUniqueValues": 3 }
        }
      ]
    }
  ]
}
```

---

## Physics - Simple Machines

### Grade 8-9: Levers and Torque

#### Question 14: Balancing Torques
**Original Question:**
> "A 2 kg mass sits 0.5 m from a fulcrum. Where should you place a 1 kg mass to balance the lever?"

**Simulation:** balancing-act

**Assessment Type:** target_achievement

**Generated Blueprint:**
```json
{
  "title": "Torque Balance Challenge",
  "narrativeIntro": "For balance: τ₁ = τ₂, so m₁×d₁ = m₂×d₂. If 2kg × 0.5m = 1kg × d₂, then d₂ = 1.0m. Find this position!",
  "tasks": [
    {
      "id": "task_setup",
      "title": "Place the First Mass",
      "description": "Place a 2 kg mass at 0.5 m from the fulcrum on the left side",
      "checkpoints": [
        {
          "id": "cp_first_mass_placed",
          "condition": { "type": "property_range", "property": "leftMassDistance", "min": 0.45, "max": 0.55 }
        }
      ]
    },
    {
      "id": "task_balance",
      "title": "Balance the Lever",
      "description": "Place a 1 kg mass on the right side to achieve balance",
      "checkpoints": [
        {
          "id": "cp_second_mass_placed",
          "condition": { "type": "property_range", "property": "rightMassCount", "min": 1, "max": 5 }
        },
        {
          "id": "cp_correct_position",
          "description": "1 kg mass should be at 1.0 m from fulcrum",
          "condition": { "type": "property_range", "property": "rightMassDistance", "min": 0.95, "max": 1.05 }
        },
        {
          "id": "cp_balanced",
          "condition": { "type": "property_equals", "property": "isBalanced", "value": true }
        }
      ]
    }
  ]
}
```

---

## Summary: Curriculum Questions Quick Reference

| Grade | Subject | Original Question | Simulation | Assessment Type |
|-------|---------|------------------|------------|-----------------|
| 9-10 | Physics | Calculate projectile range from cliff | projectile-motion | target_achievement |
| 9-10 | Physics | Find angle for maximum range | projectile-motion | parameter_discovery |
| 11-12 | Physics | Energy conservation: find speed at bottom | energy-skate-park | prediction_verification |
| 11-12 | Physics | Minimum force to overcome friction | forces-and-motion | target_achievement |
| 10-11 | Physics | Find pendulum length for T=2s | pendulum-lab | measurement |
| 10-11 | Physics | Wave speed = frequency × wavelength | wave-on-a-string | parameter_discovery |
| 8-9 | Chemistry | Observe phase transitions of water | states-of-matter | exploration |
| 10-11 | Chemistry | Demonstrate Boyle's Law (PV=k) | gas-properties | parameter_discovery |
| 10-11 | Chemistry | Demonstrate Charles's Law (V/T=k) | gas-properties | parameter_discovery |
| 9-10 | Physics | Verify Ohm's Law (V=IR) | circuit-construction-kit | construction |
| 9-10 | Physics | Series vs parallel brightness | circuit-construction-kit | comparative_analysis |
| 11-12 | Physics | Factors affecting induced EMF | faradays-law | parameter_discovery |
| 11-12 | Physics | Verify Kepler's Third Law | gravity-and-orbits | measurement |
| 8-9 | Physics | Balance a lever using torques | balancing-act | target_achievement |

---

## How Agents Transform Curriculum Questions

### Pattern: Calculation Verification
**Input:** "Calculate X using formula Y"
**Output:** Setup → Calculate → Configure simulation → Verify

### Pattern: Relationship Discovery
**Input:** "How does A affect B?"
**Output:** Control variables → Vary A systematically → Observe B → Find pattern

### Pattern: Build and Test
**Input:** "Build/construct X that does Y"
**Output:** Construction checkpoints → Functionality verification

### Pattern: Compare and Contrast
**Input:** "Compare X vs Y configuration"
**Output:** Build first → Observe → Build second → Compare metrics

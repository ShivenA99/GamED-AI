"""
PhET Bridge Config Generator Agent

Generates the configuration for the GamED-PhET bridge module.
This configuration tells the frontend what properties to track,
what interactions to monitor, and how to communicate with the simulation.
"""

from typing import Dict, Any, Optional, List, Set

from app.agents.state import AgentState
from app.agents.instrumentation import InstrumentedAgentContext
from app.agents.schemas.phet_simulation import SIMULATION_CATALOG
from app.utils.logging_config import get_logger

logger = get_logger("gamed_ai.agents.phet_bridge_config_generator")


def _to_short_name(phetio_id: str) -> str:
    """Extract short name from PhET-iO ID."""
    parts = phetio_id.split(".")
    last_part = parts[-1] if parts else phetio_id
    if last_part.endswith("Property"):
        last_part = last_part[:-8]
    return last_part


def _extract_checkpoint_requirements(blueprint: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Extract what properties, interactions, and outcomes are needed by checkpoints."""
    required = {
        "properties": set(),
        "interactions": set(),
        "outcomes": set()
    }

    for task in blueprint.get("tasks", []):
        for checkpoint in task.get("checkpoints", []):
            for condition in checkpoint.get("conditions", []):
                cond_type = condition.get("type", "").lower()

                if cond_type in ["property_equals", "property_range", "property_changed"]:
                    prop_id = condition.get("propertyId")
                    if prop_id:
                        required["properties"].add(prop_id)

                elif cond_type == "interaction_occurred":
                    int_id = condition.get("interactionId")
                    if int_id:
                        required["interactions"].add(int_id)

                elif cond_type == "outcome_achieved":
                    out_id = condition.get("outcomeId")
                    if out_id:
                        required["outcomes"].add(out_id)

                elif cond_type == "exploration_breadth":
                    param_ids = condition.get("parameterIds", [])
                    required["properties"].update(param_ids)

    return required


async def phet_bridge_config_generator_agent(
    state: AgentState,
    ctx: Optional[InstrumentedAgentContext] = None
) -> Dict[str, Any]:
    """
    Generate bridge configuration from blueprint.

    Args:
        state: Current agent state with blueprint
        ctx: Optional instrumentation context

    Returns:
        Updated state with bridge config added to blueprint
    """
    logger.info("PhET Bridge Config Generator: Creating bridge configuration")

    blueprint = state.get("blueprint", {})

    if not blueprint.get("templateType") == "PHET_SIMULATION":
        logger.error("PhET Bridge Config Generator: Invalid blueprint type")
        return {
            **state,
            "current_agent": "phet_bridge_config_generator",
            "error_message": "Blueprint is not PHET_SIMULATION type"
        }

    sim_config = blueprint.get("simulation", {})
    sim_id = sim_config.get("simulationId")

    # Get catalog entry for phetioIds
    catalog_entry = SIMULATION_CATALOG.get(sim_id, {})

    # Build list of properties to track
    properties_to_track = []
    for param in catalog_entry.get("parameters", []):
        properties_to_track.append({
            "name": _to_short_name(param["phetioId"]),
            "phetioId": param["phetioId"],
            "type": param.get("type", "number"),
            "unit": param.get("unit"),
            "min": param.get("min"),
            "max": param.get("max")
        })

    # Also add from blueprint simulation config
    for param in sim_config.get("parameters", []):
        short_name = _to_short_name(param.get("phetioId", ""))
        if short_name and not any(p["name"] == short_name for p in properties_to_track):
            properties_to_track.append({
                "name": short_name,
                "phetioId": param.get("phetioId", ""),
                "type": param.get("type", "number"),
                "unit": param.get("unit"),
                "min": param.get("min"),
                "max": param.get("max")
            })

    # Build list of interactions to track
    interactions_to_track = []
    for interaction in catalog_entry.get("interactions", []):
        interactions_to_track.append({
            "id": interaction["id"],
            "phetioId": interaction.get("phetioId", ""),
            "type": interaction.get("type", "button_click"),
            "name": interaction.get("name", interaction["id"]),
            "dataFields": interaction.get("dataFields", [])
        })

    # Also add from blueprint
    for interaction in sim_config.get("interactions", []):
        if not any(i["id"] == interaction["id"] for i in interactions_to_track):
            interactions_to_track.append({
                "id": interaction["id"],
                "phetioId": interaction.get("phetioId", ""),
                "type": interaction.get("type", "button_click"),
                "name": interaction.get("name", interaction["id"]),
                "dataFields": interaction.get("dataFields", [])
            })

    # Build list of outcomes to track
    outcomes_to_track = []
    for outcome in catalog_entry.get("outcomes", []):
        outcomes_to_track.append({
            "id": outcome["id"],
            "phetioId": outcome.get("phetioId", ""),
            "name": outcome["name"],
            "unit": outcome.get("unit")
        })

    # Also add from blueprint
    for outcome in sim_config.get("outcomes", []):
        if not any(o["id"] == outcome["id"] for o in outcomes_to_track):
            outcomes_to_track.append({
                "id": outcome["id"],
                "phetioId": outcome.get("phetioId", ""),
                "name": outcome["name"],
                "unit": outcome.get("unit")
            })

    # Extract what checkpoints need
    requirements = _extract_checkpoint_requirements(blueprint)

    # Build bridge configuration
    bridge_config = {
        "simulationId": sim_id,
        "version": sim_config.get("version", "latest"),
        "localPath": sim_config.get("localPath"),
        "screen": sim_config.get("screen"),

        # What to track
        "trackProperties": properties_to_track,
        "trackInteractions": interactions_to_track,
        "trackOutcomes": outcomes_to_track,

        # What checkpoints need
        "requiredProperties": list(requirements["properties"]),
        "requiredInteractions": list(requirements["interactions"]),
        "requiredOutcomes": list(requirements["outcomes"]),

        # Initial state
        "initialState": sim_config.get("initialState", {}),

        # Hidden/disabled elements
        "hiddenElements": sim_config.get("hiddenElements", []),
        "disabledElements": sim_config.get("disabledElements", []),

        # Communication config
        "messagePrefix": "PHET_",
        "debounceMs": 100,
        "batchUpdates": True,

        # State polling (fallback for non-phetio simulations)
        "pollIntervalMs": 500,
        "usePolling": False,  # Only enable if postMessage not available

        # Event types to emit
        "emitStateChanges": True,
        "emitInteractions": True,
        "emitOutcomes": True
    }

    # Add bridge config to blueprint
    updated_blueprint = {**blueprint, "bridgeConfig": bridge_config}

    logger.info(
        f"PhET Bridge Config Generator: Configured tracking for "
        f"{len(properties_to_track)} properties, "
        f"{len(interactions_to_track)} interactions, "
        f"{len(outcomes_to_track)} outcomes"
    )

    if ctx:
        ctx.complete({
            "blueprint": updated_blueprint,
            "current_agent": "phet_bridge_config_generator",
            "generation_complete": True
        })

    return {
        **state,
        "blueprint": updated_blueprint,
        "current_agent": "phet_bridge_config_generator",
        "generation_complete": True
    }


def generate_bridge_injection_code(bridge_config: Dict[str, Any]) -> str:
    """
    Generate JavaScript code to inject into PhET simulation for bridging.

    This code can be injected into modified PhET simulations to enable
    communication with the GamED wrapper.

    Args:
        bridge_config: Bridge configuration

    Returns:
        JavaScript code string
    """
    properties = bridge_config.get("trackProperties", [])
    interactions = bridge_config.get("trackInteractions", [])
    outcomes = bridge_config.get("trackOutcomes", [])
    prefix = bridge_config.get("messagePrefix", "PHET_")

    code = f'''
// GamED Bridge Module - Auto-generated
(function() {{
  const GAMED_BRIDGE = {{
    simulationId: "{bridge_config.get('simulationId', '')}",
    messagePrefix: "{prefix}",
    debounceMs: {bridge_config.get('debounceMs', 100)},

    // State tracking
    trackedProperties: {{}},
    pendingUpdates: {{}},
    debounceTimer: null,

    // Initialize bridge
    init: function(phetModel) {{
      this.model = phetModel;
      this.setupPropertyTracking();
      this.setupInteractionTracking();
      this.sendMessage('BRIDGE_READY', {{ simulationId: this.simulationId }});
    }},

    // Setup property tracking
    setupPropertyTracking: function() {{
      const properties = {[{', '.join([f'"{p["name"]}"' for p in properties])}]};

      properties.forEach(propName => {{
        const property = this.findProperty(propName);
        if (property && property.link) {{
          property.link((value, oldValue) => {{
            this.queuePropertyUpdate(propName, value, oldValue);
          }});
          this.trackedProperties[propName] = property.value;
        }}
      }});
    }},

    // Find property in model
    findProperty: function(name) {{
      // Try common paths
      const paths = [
        this.model,
        this.model && this.model.model,
        window.phet && window.phet.joist && window.phet.joist.sim
      ];

      for (const obj of paths) {{
        if (obj && obj[name + 'Property']) {{
          return obj[name + 'Property'];
        }}
      }}
      return null;
    }},

    // Queue property update (debounced)
    queuePropertyUpdate: function(property, value, oldValue) {{
      this.pendingUpdates[property] = {{ value, oldValue, timestamp: Date.now() }};

      if (this.debounceTimer) clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => this.flushUpdates(), this.debounceMs);
    }},

    // Flush pending updates
    flushUpdates: function() {{
      if (Object.keys(this.pendingUpdates).length === 0) return;

      this.sendMessage('STATE_BATCH', {{
        updates: this.pendingUpdates,
        timestamp: Date.now()
      }});

      this.pendingUpdates = {{}};
    }},

    // Track interaction
    trackInteraction: function(interactionId, data) {{
      this.sendMessage('INTERACTION', {{
        interactionId,
        data: data || {{}},
        timestamp: Date.now()
      }});
    }},

    // Track outcome
    trackOutcome: function(outcomeId, value, unit) {{
      this.sendMessage('OUTCOME', {{
        outcomeId,
        value,
        unit,
        timestamp: Date.now()
      }});
    }},

    // Send message to parent
    sendMessage: function(type, payload) {{
      if (window.parent && window.parent !== window) {{
        window.parent.postMessage({{
          type: this.messagePrefix + type,
          simulationId: this.simulationId,
          ...payload
        }}, '*');
      }}
    }},

    // Handle incoming messages
    handleMessage: function(event) {{
      const data = event.data;
      if (!data || !data.type || !data.type.startsWith(this.messagePrefix)) return;

      const type = data.type.replace(this.messagePrefix, '');

      switch (type) {{
        case 'SET_PROPERTY':
          this.setProperty(data.property, data.value);
          break;
        case 'GET_STATE':
          this.sendCurrentState();
          break;
        case 'RESET':
          this.reset();
          break;
      }}
    }},

    // Set property value
    setProperty: function(name, value) {{
      const property = this.findProperty(name);
      if (property && property.set) {{
        property.set(value);
      }}
    }},

    // Send current state
    sendCurrentState: function() {{
      const state = {{}};
      for (const name in this.trackedProperties) {{
        const property = this.findProperty(name);
        if (property) {{
          state[name] = property.value;
        }}
      }}
      this.sendMessage('CURRENT_STATE', {{ state }});
    }},

    // Reset simulation
    reset: function() {{
      if (this.model && this.model.reset) {{
        this.model.reset();
      }}
    }}
  }};

  // Listen for messages from parent
  window.addEventListener('message', (e) => GAMED_BRIDGE.handleMessage(e));

  // Export for initialization
  window.GAMED_BRIDGE = GAMED_BRIDGE;

  // Auto-init when simulation is ready
  if (window.phet && window.phet.joist && window.phet.joist.sim) {{
    GAMED_BRIDGE.init(window.phet.joist.sim);
  }} else {{
    document.addEventListener('DOMContentLoaded', () => {{
      const checkReady = setInterval(() => {{
        if (window.phet && window.phet.joist && window.phet.joist.sim) {{
          clearInterval(checkReady);
          GAMED_BRIDGE.init(window.phet.joist.sim);
        }}
      }}, 100);
    }});
  }}
}})();
'''

    return code

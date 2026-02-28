# Troubleshooting

Common issues and debugging strategies for GamED.AI v2.

---

## Backend Won't Start

**Port already in use:**
```bash
lsof -i:8000                    # Check what's using the port
lsof -ti:8000 | xargs kill -9  # Kill the process
```

**Virtual environment not activated:**
```bash
which python  # Should show backend/venv/bin/python
cd backend && source venv/bin/activate
```

**Missing dependencies:**
```bash
cd backend && pip install -r requirements.txt
```

---

## Import Errors

Always run from the `backend/` directory with `PYTHONPATH=.`:

```bash
cd backend && PYTHONPATH=. python script.py
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Common import error patterns:
- `ModuleNotFoundError: No module named 'app'` → Missing `PYTHONPATH=.`
- `ModuleNotFoundError: No module named 'app.agents.my_agent'` → File doesn't exist or naming mismatch
- Circular imports → Check that agents don't import each other directly; use state dict for data passing

---

## Database Issues

**Reset database (tables auto-created on restart):**
```bash
rm backend/gamed_ai.db
# Then restart the server
```

**Wrong database file:**
Check for `gamed_ai.db` vs `gamed_ai_v2.db` confusion. The default is `gamed_ai.db`. Verify `DATABASE_URL` in environment.

**Table doesn't exist:**
```bash
sqlite3 backend/gamed_ai.db ".tables"  # List all tables
```
If tables are missing, restart the server — SQLAlchemy creates them on startup.

**Schema mismatch after model changes:**
Delete the database and restart. SQLite doesn't support `ALTER TABLE` well, so a fresh start is cleanest during development.

---

## Frontend Build Errors

**Clean rebuild:**
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

**TypeScript errors:**
```bash
cd frontend && npx tsc --noEmit  # Check without building
```

**Common fixes:**
- Type errors in pipeline components → Check `AGENT_METADATA` matches actual agent names
- Missing module → Run `npm install`
- Next.js cache corruption → Delete `.next/` directory

---

## Pipeline Debugging

### State Field Propagation

The most common pipeline failure. Check these in order:

1. **Is the field defined in `AgentState`?**
   - File: `backend/app/agents/state.py`
   - Every field an agent reads or writes must be in the TypedDict

2. **Is the upstream agent writing the field?**
   - Check the agent's return dict — does it include the field name?
   - The field name in the return dict must exactly match the AgentState key

3. **Is the downstream agent reading the correct key?**
   - `state.get("field_name")` vs `state["field_name"]` — use `.get()` for optional fields

4. **Is the field registered in instrumentation?**
   - `extract_input_keys()` and `extract_output_keys()` in `instrumentation.py`
   - Missing registration won't break the pipeline but will break observability

### Graph Wiring

1. **Is the agent node added?**
   ```python
   graph.add_node("agent_name", wrap_agent_with_instrumentation(agent_fn, "agent_name"))
   ```

2. **Are edges connected?**
   ```python
   graph.add_edge("previous_agent", "agent_name")
   graph.add_edge("agent_name", "next_agent")
   ```

3. **Is `wrap_agent_with_instrumentation()` applied?**
   - Without it, the agent runs but produces no observability data

4. **Conditional edges correct?**
   - Check the routing function returns the right string keys
   - Check the edge map matches those keys to agent names

### ID Field Confusion

The pipeline uses several ID fields that serve different purposes:

| Field | Purpose | Where Set |
|-------|---------|-----------|
| `question_id` | Unique ID for the input question | API request or auto-generated |
| `_run_id` | Pipeline execution run ID | Pipeline orchestrator |
| `process_id` | Database record ID | Database layer |

Don't mix these up when querying observability data or debugging state.

### Workflow Mode Issues

Check logs for workflow mode detection:
```
"Using workflow mode" → workflow_execution_plan is populated
"Legacy mode" → workflow_execution_plan is empty/None
```

If workflow mode isn't activating when expected:
1. Check `scene_breakdown` is populated by GamePlanner
2. Check `workflow_execution_plan` is populated by AssetPlanner
3. Check `check_workflow_mode()` routing function in `graph.py`

### Preset Pipeline Issues

If the wrong preset pipeline is running:
1. Check `_pipeline_preset` state field
2. Check `PIPELINE_PRESET` environment variable
3. Check `should_use_preset_pipeline()` routing function
4. Check `get_compiled_graph()` factory function in `graph.py`

---

## Common Agent Bugs

### LLM Response Parsing Failures

**Symptoms:** Agent throws JSON parse error, blueprint validation fails

**Fixes:**
- Check if `json_repair` service is being used for LLM JSON outputs
- Verify the prompt asks for JSON output explicitly
- Check token limits — truncated responses break JSON parsing
- Look for markdown code fences in LLM output that need stripping

### Zone Detection Returns Empty

**Symptoms:** `diagram_zones` is empty, blueprint has no zones

**Fixes:**
- Check `image_classification` — is the labeled/unlabeled detection correct?
- For labeled: check `annotation_elements` from QwenAnnotationDetector
- For unlabeled: check DirectStructureLocator VLM response
- Check image URL accessibility — is the diagram image actually downloadable?
- SAM3 model path — verify `SAM2_MODEL_PATH` is set correctly

### Blueprint Validation Retry Loop

**Symptoms:** Blueprint validator fails 3 times, pipeline errors out

**Fixes:**
- Read the validation error messages — they describe exactly what's wrong
- Check if upstream state fields (zones, labels, game_plan) are populated
- Don't increase `max_retries` — fix the root cause
- Common: zone count mismatch between `diagram_zones` and `diagram_labels`

### Multi-Scene Pipeline Stalls

**Symptoms:** Pipeline hangs or errors during multi-scene generation

**Fixes:**
- Check `scene_breakdown` structure — each scene needs mechanics and content
- Check `current_scene_number` increments correctly
- Check `scene_images`, `scene_zones`, `scene_labels` are populated per-scene
- Verify `MultiSceneOrchestrator` is wired in graph for the current preset

---

## Rate Limiting and API Errors

**Groq free tier:**
- 30 requests/minute, 6000 tokens/minute limits
- Pipeline may need delays between agents
- Check for silent failures in sub-agent parallel execution

**Serper API:**
- Image search has separate quota from web search
- Check `SERPER_API_KEY` is valid

**Ollama/local models:**
- Check `OLLAMA_BASE_URL` is reachable
- Check model is downloaded: `ollama list`
- Memory pressure on large models — check system RAM

---

## Observability Not Showing Data

1. **Agent not wrapped with instrumentation:**
   - Check `wrap_agent_with_instrumentation()` is applied in `graph.py`

2. **Input/output keys not registered:**
   - Check `extract_input_keys()` and `extract_output_keys()` in `instrumentation.py`

3. **Frontend metadata missing:**
   - Check `AGENT_METADATA` in `PipelineView.tsx` has an entry for the agent
   - Check `GRAPH_LAYOUT` includes the agent

4. **Database not persisting:**
   - Check `DATABASE_URL` environment variable
   - Check write permissions on the database file

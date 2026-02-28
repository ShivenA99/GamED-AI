# Reducing Input Token Costs in Multi-Agent ReAct Pipelines

## Deep Research Report — February 2026

**Context:** GamED.AI pipeline with 4-5 sequential ReAct agents, ~54,000 input tokens per run.
**Breakdown:** ~22K core prompts, ~10K tool results, ~10K state serialization, ~5K tool implementations, ~7K retry overhead.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Academic Research](#2-academic-research)
3. [Provider-Level Optimizations](#3-provider-level-optimizations)
4. [Framework-Level Strategies](#4-framework-level-strategies)
5. [Technique Deep Dives](#5-technique-deep-dives)
6. [Architecture-Specific Recommendations](#6-architecture-specific-recommendations)
7. [Token Savings Estimates](#7-token-savings-estimates)
8. [Priority Implementation Order](#8-priority-implementation-order)
9. [Code Patterns](#9-code-patterns)
10. [Sources](#10-sources)

---

## 1. Executive Summary

Based on extensive research across academic papers (NeurIPS, ICLR, ACL, EMNLP, NAACL 2023-2026), industry blog posts, framework documentation, and provider APIs, the following key findings emerge:

1. **Prompt caching alone can reduce costs by 45-80%** for the static prefix portion of each agent call (system prompt + tool definitions). This is the single highest-impact, lowest-effort optimization.

2. **Observation masking (removing old tool results from history) reduces costs by ~50%** with no measurable quality degradation — and is simpler than LLM-based summarization (NeurIPS 2025 finding).

3. **Dynamic tool loading reduces tool definition tokens by 60-96%** by only loading schemas when the agent actually needs them, rather than passing all tool definitions upfront.

4. **State projection (passing only needed fields) can eliminate 60-80% of serialization tokens** since each downstream agent typically needs only 2-5 fields from a 4K-token upstream state object.

5. **Compact serialization formats (TOON) reduce structured data tokens by 35-60%** compared to formatted JSON.

6. **Context folding/compression (ACON, AgentFold, PAACE) reduces peak tokens by 26-54%** while preserving task success rates above 95%.

7. **Combined, these techniques can reduce the 54K baseline to approximately 12-18K tokens per pipeline run (67-78% reduction).**

---

## 2. Academic Research

### 2.1 Context Compression Frameworks

#### ACON: Optimizing Context Compression for Long-horizon LLM Agents
- **Source:** Kang et al., arXiv 2510.00615, October 2025
- **URL:** https://arxiv.org/abs/2510.00615
- **Key Findings:** ACON provides a unified framework for systematic and adaptive context compression. It uses a failure-driven, task-aware compression guideline optimization process that is gradient-free and applicable to API-based models. Experiments on AppWorld, OfficeBench, and Multi-objective QA show 26-54% reduction in peak tokens while preserving task success. Optimized compressors can be distilled into smaller models, retaining 95%+ accuracy.
- **Relevance to GamED.AI:** High. The failure-driven optimization approach means compression guidelines improve over time based on actual pipeline failures. Could be applied to each ReAct agent's context independently.

#### AgentFold: Long-Horizon Web Agents with Proactive Context Management
- **Source:** Tongji Lab, Alibaba Group, arXiv 2510.24699, October 2025
- **URL:** https://arxiv.org/abs/2510.24699
- **Key Findings:** Treats context as a dynamic cognitive workspace rather than a passive log. Learns to execute "folding" operations at multiple scales — granular condensations for vital details, deep consolidations for entire sub-tasks. Achieves only 7K tokens after 100 turns of interaction and scales to 500 turns. Surpasses models of dramatically larger scale.
- **Relevance to GamED.AI:** Very high. The multi-scale folding concept directly applies to our ReAct loops where some tool results are critical (zone coordinates) while others are informational (domain knowledge retrieval).

#### PAACE: Plan-Aware Automated Agent Context Engineering
- **Source:** arXiv 2512.16970, December 2025
- **URL:** https://arxiv.org/abs/2512.16970
- **Key Findings:** Optimizes evolving agent state through next-k-task relevance modeling, plan-structure analysis, and function-preserving compression. On AppWorld, achieves higher accuracy than all baselines while lowering peak context. Distilled PAACE-FT retains 97% of teacher performance while reducing inference cost by over an order of magnitude.
- **Relevance to GamED.AI:** Very high. The "next-k-task relevance modeling" concept directly maps to our sequential pipeline where each agent knows what downstream agents need.

#### U-Fold: Dynamic Intent-Aware Context Folding
- **Source:** Su et al., arXiv 2601.18285, January 2026
- **URL:** https://arxiv.org/abs/2601.18285
- **Key Findings:** Retains full user-agent dialogue and tool-call history but produces intent-aware, evolving dialogue summaries and compact, task-relevant tool logs. Achieves 71.4% win rate over ReAct in long-context settings with up to 27% improvement over prior folding baselines.
- **Relevance to GamED.AI:** Moderate. More relevant for multi-turn user-facing agents, but the intent-aware folding concept applies to our tool result management.

#### Active Context Compression: Autonomous Memory Management
- **Source:** arXiv 2601.07190, January 2026
- **URL:** https://arxiv.org/abs/2601.07190
- **Key Findings:** LLM agents autonomously decide when to consolidate key learnings into a persistent "Knowledge" block and prune raw interaction history. Key finding: current LLMs require explicit prompting to compress regularly (every 10-15 tool calls) — they do not naturally optimize for context efficiency without scaffolding.
- **Relevance to GamED.AI:** High. Our ReAct agents run 3-6 tool iterations, well within the range where explicit compression triggers are effective.

### 2.2 Communication Pruning in Multi-Agent Systems

#### AgentPrune (Cut the Crap) — ICLR 2025
- **Source:** Yue et al., ICLR 2025
- **URL:** https://arxiv.org/abs/2410.02506
- **Key Findings:** First to formally define communication redundancy in LLM-based multi-agent pipelines. Performs one-shot pruning on spatial-temporal message-passing graphs. Achieves 28.1-72.8% token reduction while integrating seamlessly into existing frameworks. Reduced costs from $43.7 to $5.6 on benchmark tasks.
- **Relevance to GamED.AI:** High. Our sequential pipeline passes full state between agents — AgentPrune's approach of pruning the inter-agent communication graph directly applies.

#### AgentDropout — ACL 2025
- **Source:** Wang et al., ACL 2025
- **URL:** https://aclanthology.org/2025.acl-long.1170/
- **Key Findings:** Dynamically identifies and eliminates redundant agents and communication across different rounds by optimizing adjacency matrices of communication graphs. Achieves 21.6% reduction in prompt tokens and 18.4% in completion tokens with 1.14 performance improvement.
- **Relevance to GamED.AI:** Moderate. More applicable to debate-style multi-agent systems, but the concept of dynamically eliminating redundant communication rounds applies to our retry logic.

### 2.3 Observation Masking vs. Summarization

#### The Complexity Trap — NeurIPS 2025 (DL4Code Workshop)
- **Source:** Lindenbauer, Slinko et al., JetBrains Research, NeurIPS 2025
- **URL:** https://arxiv.org/abs/2508.21433
- **GitHub:** https://github.com/JetBrains-Research/the-complexity-trap
- **Key Findings:** Simple observation masking (removing tool outputs from history while preserving action/reasoning history) halves cost while matching or exceeding LLM summarization solve rates. With Qwen3-Coder 480B: observation masking costs $0.61/instance (52.7% reduction from $1.29 baseline) vs LLM-Summary at $0.64. A hybrid approach further reduces costs by 7-11%.
- **Relevance to GamED.AI:** **Critical.** This is the most directly applicable finding. Our ReAct loops replay full tool results (zone detection outputs, image analysis, etc.) on every iteration. Simply masking old tool results would halve our per-agent token cost with zero quality loss.

### 2.4 Prompt Compression Techniques

#### LLMLingua / LLMLingua-2 — EMNLP 2023, ACL 2024
- **Source:** Microsoft Research
- **URL:** https://github.com/microsoft/LLMLingua
- **Key Findings:** Achieves up to 20x compression while preserving prompt capabilities. LLMLingua-2 uses BERT-level encoder for token classification, offering 3x-6x faster performance than LLMLingua. Integrated into LangChain and LlamaIndex.
- **Relevance to GamED.AI:** Moderate. Effective for compressing domain knowledge text and system prompts, but adds latency from the compression model. Best suited for pre-processing static content.

#### Selective Context — EMNLP 2023
- **Source:** Li et al., EMNLP 2023
- **URL:** https://aclanthology.org/2023.emnlp-main.391/
- **GitHub:** https://github.com/liyucheng09/Selective_Context
- **Key Findings:** Uses information entropy to evaluate token importance. Achieves 50% context reduction with only .023 BERTscore drop and .038 faithfulness drop. 36% reduction in inference memory, 32% reduction in inference time.
- **Relevance to GamED.AI:** Moderate. Could be applied to compress domain knowledge passages before injection into agent context.

#### ICAE: In-Context Autoencoder — ICLR 2024
- **Source:** arXiv 2307.06945
- **URL:** https://arxiv.org/abs/2307.06945
- **Key Findings:** Compresses long context into short compact memory slots using LoRA-adapted encoder. Achieves 4x context compression with ~1% additional parameters. Related approaches include Gisting (Mu et al., 2023) and AutoCompressor (Chevalier et al., 2023).
- **Relevance to GamED.AI:** Low for our architecture. Requires model fine-tuning, not applicable to API-based models.

#### Prompt Compression Survey — NAACL 2025 (Oral)
- **Source:** Li et al., NAACL 2025
- **URL:** https://aclanthology.org/2025.naacl-long.368/
- **GitHub:** https://github.com/ZongqianLi/Prompt-Compression-Survey
- **Key Findings:** Comprehensive taxonomy dividing techniques into hard prompt methods (token removal, paraphrasing) and soft prompt methods (compression into special tokens). Hard prompt methods are API-compatible; soft prompt methods require model access. Future directions include combining both approaches and leveraging multimodality.
- **Relevance to GamED.AI:** Reference material. Use this taxonomy to evaluate which compression techniques fit our API-based architecture.

### 2.5 Efficient Agent Memory

#### SimpleMem — January 2026
- **Source:** University of North Carolina at Chapel Hill
- **URL:** https://arxiv.org/abs/2601.02553
- **GitHub:** https://github.com/aiming-lab/SimpleMem
- **Key Findings:** Three-stage pipeline: semantic structured compression, online semantic synthesis, and intent-aware retrieval planning. Achieves 30x token reduction (550 vs 17,000 tokens) with 26% F1 improvement. Works across Claude, GPT-4, and small open-source models.
- **Relevance to GamED.AI:** Moderate. More relevant for long-running conversational agents, but the semantic synthesis concept applies to consolidating tool results within a single ReAct loop.

---

## 3. Provider-Level Optimizations

### 3.1 Anthropic Prompt Caching

- **URL:** https://docs.claude.com/en/docs/build-with-claude/prompt-caching
- **Pricing:** Cache writes cost 25% more than base input; cache reads cost only 10% of base input (90% discount).
- **Requirements:** Minimum 1,024 tokens per cache checkpoint, up to 4 checkpoints per request, 5-minute TTL (extended to 1 hour with regular hits).
- **Multi-turn optimization:** Using multiple user message breakpoints provides 15-25% cost savings compared to single breakpoint.
- **Cache-aware rate limits:** Cache read tokens no longer count against ITPM limits for Claude 3.7 Sonnet.
- **Best practice:** Place static content (system prompt, tool definitions, mechanic encyclopedias) at the beginning. Put variable content (conversation history, task-specific state) at the end.

### 3.2 Anthropic Token-Efficient Tool Use

- **URL:** https://docs.anthropic.com/en/docs/build-with-claude/tool-use/token-efficient-tool-use
- **Feature:** Beta header `token-efficient-tools-2025-02-19` reduces output token consumption by up to 70% (average 14% reduction).
- **Availability:** Claude 3.7 Sonnet on API, Bedrock, and Vertex AI. Not needed for Claude 4+ models.
- **Impact:** Reduces output tokens for tool call responses, meaning less history accumulation in ReAct loops.

### 3.3 OpenAI Automatic Prefix Caching

- **URL:** https://platform.openai.com/docs/guides/prompt-caching
- **Mechanism:** Automatically caches prompts longer than 1,024 tokens. Caches the longest matching prefix in 128-token increments.
- **Pricing:** Cached tokens cost 50% less than regular input tokens.
- **Tool definitions:** Both the messages array and tool definitions contribute to the cacheable prefix.
- **Retention:** 5-10 minutes of inactivity, up to 1 hour standard, up to 24 hours with extended caching.
- **Best practice:** Place static content first; tool schemas are included in the cacheable prefix.

### 3.4 Google Gemini Context Caching

- **URL:** https://ai.google.dev/gemini-api/docs/pricing
- **Pricing:** Cache reads cost 10% of base input price. Storage: $1-4.50 per million tokens per hour.
- **Batch Mode:** Offers 50% discount over real-time for bulk processing.
- **Note:** Gemini 1.5 Pro charges 2x for inputs >200K tokens, incentivizing efficient prompt engineering.

### 3.5 Prompt Caching for Agentic Tasks

#### "Don't Break the Cache" — January 2026
- **Source:** arXiv 2601.06007
- **URL:** https://arxiv.org/abs/2601.06007
- **Key Findings:** Evaluated three caching strategies across OpenAI, Anthropic, and Google: full context caching, system prompt only caching, and caching excluding dynamic tool results. Strategic cache block control (placing dynamic content at end, excluding dynamic tool results) provides more consistent benefits than naive full-context caching. Full-context caching can paradoxically increase latency. Prompt caching reduces API costs by 45-80% and improves time to first token by 13-31%.
- **Critical insight for GamED.AI:** Do NOT try to cache conversation history or tool results — cache only the system prompt + tool definitions prefix. Structure each agent's prompt with the static prefix first, then variable content.

---

## 4. Framework-Level Strategies

### 4.1 LangGraph Message Management

- **URL:** https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-manage-message-history/
- **Key features:**
  - `trim_messages(max_tokens=N, strategy="last")` — keeps only the last N tokens of message history
  - `count_tokens_approximately()` — fast approximate token counting for hot-path use
  - `pre_model_hook` in `create_react_agent` — intercept and transform messages before LLM call
  - Summarization nodes that condense history when it exceeds a threshold
- **Implementation:** Define a `pre_model_hook` function that takes graph state and returns trimmed/summarized messages as LLM input.

### 4.2 LangChain Deep Agents Context Management

- **URL:** https://blog.langchain.com/context-management-for-deepagents/
- **Three compression techniques:**
  1. **Tool result offloading:** Tool responses >20,000 tokens are offloaded to filesystem, replaced with file path + 10-line preview
  2. **Tool input offloading:** At 85% context capacity, old write/edit arguments are replaced with filesystem pointers
  3. **Summarization:** When offloading is exhausted, LLM generates structured summary (session intent, artifacts, decisions, next steps) replacing full history
- **Relevance:** The 20K threshold is too high for our use case (our total is 54K), but the tiered approach (offload first, summarize second) is the right pattern. We should set thresholds relative to our context budget.

### 4.3 Google ADK Context Compaction

- **URL:** https://google.github.io/adk-docs/context/compaction/
- **Mechanism:** Sliding window approach. Compacts older events using LLM summarization once a threshold number of workflow events is reached.
- **Configuration:**
  - `compaction_interval` — number of completed events that triggers compaction
  - `overlap_size` — number of previously compacted events included in new compaction
  - Optional `summarizer` — specific model for summarization (can use cheaper model)
- **Relevance:** Good pattern for our ReAct loops. Set compaction_interval to 3 (compact after every 3 tool calls) with overlap_size of 1.

### 4.4 CrewAI Context Window Management

- **URL:** https://docs.crewai.com/en/concepts/agents
- **Feature:** `respect_context_window=True` parameter automatically detects when conversation exceeds LLM context limits and summarizes content.
- **Limitation:** Reactive rather than proactive — waits until context is full rather than proactively managing it.

### 4.5 Dynamic Tool Loading (Speakeasy)

- **URL:** https://www.speakeasy.com/blog/how-we-reduced-token-usage-by-100x-dynamic-toolsets-v2
- **Approach:** Three-step separation: `search_tools` (natural language query) -> `describe_tools` (detailed schemas on demand) -> `execute_tool` (execution with parameters).
- **Results:** 96.7% input token reduction for simple tasks, 91.2% for complex tasks. Static toolsets with 400 tools consume 400K+ tokens; dynamic toolsets use 1,300-2,500 tokens regardless of toolset size.
- **Key insight:** Schemas represent 60-80% of token usage in static toolsets. Lazy loading eliminates this overhead.
- **Relevance to GamED.AI:** Very high. Our agents have 3-6 tools each with verbose schemas. Even with fewer tools, lazy loading could save 60-80% of the ~5K tool definition tokens.

---

## 5. Technique Deep Dives

### 5.1 Observation Masking (Recommended as Primary Strategy)

**What it is:** Remove tool output content from conversation history while preserving the action/reasoning trace. The agent retains memory of what it did and why, but not the full output of each tool call.

**How it works in a ReAct loop:**
- Iteration 1: System prompt + task + tools + thought_1 + action_1 + observation_1
- Iteration 2: System prompt + task + tools + thought_1 + action_1 + [MASKED: see tool result summary] + thought_2 + action_2 + observation_2
- Iteration 3: System prompt + task + tools + thought_1 + action_1 + [MASKED] + thought_2 + action_2 + [MASKED] + thought_3 + action_3 + observation_3

**Evidence:** JetBrains "Complexity Trap" paper shows this achieves 52.7% cost reduction with equal or better solve rates than LLM summarization. The key insight: the agent's own reasoning trace (thoughts) already captures the essential information from tool results.

**Savings estimate for GamED.AI:** Tool results are ~10K tokens. With 5 agents averaging 4 iterations each, observation masking on iterations 2+ saves approximately 7.5K tokens (75% of tool result tokens). Combined with the avoided repetition of early results, effective savings: ~8-10K tokens.

### 5.2 State Projection

**What it is:** Instead of serializing the full upstream state object into each agent's task prompt, project only the specific fields that agent reads.

**Current problem:** `game_design_v3` is ~4K tokens, passed to every downstream agent, but each agent typically reads only 2-5 fields.

**Implementation:**
```python
# Instead of:
task_prompt = f"Game design: {json.dumps(state['game_design_v3'])}"

# Use field projection:
AGENT_FIELD_REQUIREMENTS = {
    "scene_architect": ["game_design_v3.template_type", "game_design_v3.mechanics", "game_design_v3.scenes"],
    "interaction_designer": ["game_design_v3.mechanics", "game_design_v3.interaction_patterns"],
    "asset_generator": ["game_design_v3.visual_style", "game_design_v3.asset_requirements"],
    "blueprint_assembler": ["game_design_v3.template_type", "game_design_v3.scoring"],
}

def project_state(state: dict, agent_name: str) -> dict:
    required_fields = AGENT_FIELD_REQUIREMENTS[agent_name]
    projected = {}
    for field_path in required_fields:
        parts = field_path.split(".")
        value = state
        for part in parts:
            value = value.get(part, {})
        projected[field_path] = value
    return projected
```

**Savings estimate:** If `game_design_v3` is 4K tokens and each agent needs ~800 tokens of it, that is a 3.2K saving per agent x 4 downstream agents = ~12.8K tokens saved from state serialization. Combined with other state objects (~6K), total savings: ~8-10K tokens.

### 5.3 Dynamic System Prompt Scoping

**What it is:** Instead of including a full "mechanic encyclopedia" in every agent's system prompt, dynamically scope it to only the mechanics relevant to the current game.

**Current problem:** System prompts contain 1-2K tokens of static mechanic definitions even when the game only uses 2 of 10 possible mechanics.

**Implementation:**
```python
MECHANIC_DEFINITIONS = {
    "drag_and_drop": "...(200 tokens)...",
    "multiple_choice": "...(200 tokens)...",
    "sequence_ordering": "...(200 tokens)...",
    # ... 10 mechanics total
}

def build_system_prompt(base_prompt: str, active_mechanics: list[str]) -> str:
    relevant_defs = {k: v for k, v in MECHANIC_DEFINITIONS.items() if k in active_mechanics}
    return base_prompt + "\n\nRelevant mechanics:\n" + json.dumps(relevant_defs)
```

**Savings estimate:** If the full encyclopedia is 2K tokens and only 2/10 mechanics are active, savings of ~1.6K tokens per agent x 5 agents = ~8K tokens. However, this reduces the cacheable static prefix, so the net benefit depends on cache hit rates.

**Trade-off:** Dynamic scoping reduces tokens but may reduce prompt caching effectiveness if the scoped content varies per run. Solution: sort mechanics deterministically and cache the most common combinations.

### 5.4 Compact Serialization (TOON Format)

**What it is:** TOON (Token-Oriented Object Notation) is a compact serialization format designed for LLM prompts that achieves 35-60% token reduction vs formatted JSON.

- **URL:** https://github.com/toon-format/toon
- **Key insight:** JSON formatting overhead (quotes, braces, commas, whitespace) consumes 40-70% of available tokens.
- **Results:** 55-60% reduction for uniform tabular data; 26.9 accuracy per 1K tokens vs 15.4 for standard JSON.
- **Best for:** Arrays of objects with identical fields (like zone definitions, label lists, scene specifications).

**Implementation for GamED.AI:**
```python
# Instead of JSON for zone definitions:
# [{"id": "zone_1", "label": "mitochondria", "x": 120, "y": 340, "w": 80, "h": 60}, ...]

# Use compact tabular format:
# zones|id,label,x,y,w,h
# zone_1,mitochondria,120,340,80,60
# zone_2,nucleus,200,180,120,100
```

**Savings estimate:** State serialization is ~10K tokens. Tabular data (zones, labels, scenes) is roughly 60% of this. TOON achieves ~50% reduction on tabular data: 10K * 0.6 * 0.5 = 3K tokens saved. Non-tabular data gets ~20% reduction: 10K * 0.4 * 0.2 = 0.8K. Total: ~3.8K tokens saved.

### 5.5 Conversation History Summarization

**What it is:** Replace earlier tool call/result pairs with a compact summary while keeping recent interactions intact.

**LangGraph implementation:**
```python
from langchain_core.messages import trim_messages

def pre_model_hook(state):
    messages = state["messages"]
    # Keep system message + last 3 interactions, summarize the rest
    trimmed = trim_messages(
        messages,
        max_tokens=4000,
        strategy="last",
        token_counter=count_tokens_approximately,
        include_system=True,
    )
    return {"messages": trimmed}
```

**Contrast with observation masking:** Summarization preserves more semantic information but costs an additional LLM call. Observation masking is free but loses detail. The "Complexity Trap" paper found masking slightly outperforms summarization, suggesting the agent's reasoning trace is sufficient.

### 5.6 Tool Schema Minimization

**What it is:** Reduce the verbosity of tool descriptions and parameter schemas sent to the LLM.

**Strategies:**
1. Use short parameter names and descriptions
2. Remove optional parameters unless the agent routinely uses them
3. Use `enum` constraints instead of verbose descriptions of valid values
4. Load full schemas lazily (Speakeasy pattern)

**Example optimization:**
```python
# Before (verbose):
{
    "name": "detect_zones",
    "description": "Detect interactive zones in a diagram image using SAM3 segmentation model. This tool analyzes the provided image and identifies distinct regions that can be used as interactive drop zones in the label diagram game.",
    "parameters": {
        "image_path": {
            "type": "string",
            "description": "The absolute file path to the diagram image that should be analyzed for zone detection"
        },
        "min_zone_area": {
            "type": "integer",
            "description": "The minimum area in pixels squared that a detected region must have to be considered a valid zone",
            "default": 100
        },
        "max_zones": {
            "type": "integer",
            "description": "The maximum number of zones to detect and return",
            "default": 20
        }
    }
}

# After (minimized):
{
    "name": "detect_zones",
    "description": "Detect interactive zones in a diagram image via SAM3 segmentation.",
    "parameters": {
        "image_path": {"type": "string", "description": "Path to diagram image"},
        "min_zone_area": {"type": "integer", "default": 100},
        "max_zones": {"type": "integer", "default": 20}
    }
}
```

**Savings estimate:** Tool definitions are ~5K tokens across 5 agents with 3-6 tools each. Minimizing descriptions typically saves 40-60%: ~2-3K tokens saved.

### 5.7 Hierarchical Sub-Agent Decomposition

**What it is:** Break one large ReAct loop with many tools into smaller focused sub-agents, each with fewer tools and less context.

**Evidence:**
- RP-ReAct separates strategic planning from execution, providing resilience to trajectory drift and context overflow.
- Hierarchical frameworks with Global Planner + Local Executor improve coherence over long sequences.
- Sub-agent delegation allows using cheaper models for routine sub-tasks.

**Application to GamED.AI:**
Instead of one `asset_generator` agent with 6 tools handling image retrieval, analysis, segmentation, and validation, split into:
1. `asset_planner` (1 tool, small model) — plans what assets are needed
2. `asset_retriever` (2 tools, medium model) — retrieves and validates images
3. `asset_processor` (2 tools, medium model) — segments and processes images

Each sub-agent carries only its relevant context, reducing per-call tokens.

**Savings estimate:** If the original agent has 6 tools (2K tokens of schemas) and 4K of accumulated history by iteration 5, splitting into 3 sub-agents with 2 tools each reduces per-call context from ~8K to ~3K per sub-agent call, with total across 3 agents being ~9K vs the original ~8K. The savings come from not accumulating cross-concern history. Net savings: ~2-4K tokens per agent that was previously monolithic.

### 5.8 Model Routing for Sub-Tasks

**What it is:** Use cheaper, faster models for simple sub-tasks within the pipeline.

**Evidence:**
- Intelligent routing handles 70-80% of traffic with small models at a fraction of the cost.
- Claude Haiku 4.5: $0.80/M input tokens vs Sonnet 4.5: $3/M input tokens (3.75x cheaper).
- GPT-4o-mini: $0.15/M input tokens (20x cheaper than GPT-4o).
- Cascade routing achieves 94%+ accuracy at one-third the cost.

**Application to GamED.AI:**
- Use Haiku/GPT-4o-mini for: input validation, schema extraction, simple classification, tool result parsing
- Use Sonnet/GPT-4o for: game design reasoning, interaction pattern design, blueprint assembly
- Use Opus only for: complex multi-step reasoning, error recovery, quality validation

**Savings estimate:** If 40% of agent calls are simple enough for Haiku (3.75x cheaper), effective cost reduction is: 0.4 * 0.73 = 29% cost reduction from model routing alone.

---

## 6. Architecture-Specific Recommendations

### 6.1 Deduplicating contextvars and Task Prompt Content

**Problem:** Python tool functions inject context via `contextvars` — the same domain knowledge appears in both the task prompt AND the tool's internal context, so when the tool result is returned, the agent sees the information three times: (1) in the task prompt, (2) embedded in the tool result, and (3) in any subsequent tool that also reads the same contextvar.

**Solution:**
```python
# Current pattern (duplicates context):
class DomainKnowledgeTool:
    def execute(self):
        context = domain_context_var.get()  # Same data as task prompt
        result = self.process(context)
        return f"Domain knowledge: {context}\nAnalysis: {result}"

# Optimized pattern (reference-based):
class DomainKnowledgeTool:
    def execute(self):
        context = domain_context_var.get()
        result = self.process(context)
        # Only return NEW information, reference existing context
        return f"Analysis (using domain context from task prompt): {result}"
```

**Additional strategy:** Audit all tool functions to identify which contextvars overlap with task prompt content. Create a `ContextRegistry` that tracks what information is already in the agent's context and prevents tools from re-injecting it.

### 6.2 ReAct Base Class History Replay Optimization

**Problem:** The ReAct base class replays full conversation history each iteration, including all previous tool calls and their full results.

**Solution — Implement tiered history management:**

```python
class OptimizedReActBase:
    def __init__(self, max_full_results: int = 2, summary_model: str = "haiku"):
        self.max_full_results = max_full_results

    def build_messages(self, iteration: int, history: list[dict]) -> list[dict]:
        messages = []
        # Always include: system prompt + task prompt (cacheable prefix)
        messages.append(self.system_message)
        messages.append(self.task_message)

        # For history: keep last N full results, mask earlier ones
        for i, entry in enumerate(history):
            if entry["role"] == "assistant":
                # Always keep the agent's reasoning
                messages.append(entry)
            elif entry["role"] == "tool":
                if i >= len(history) - (self.max_full_results * 2):
                    # Keep recent tool results in full
                    messages.append(entry)
                else:
                    # Mask old tool results with a summary
                    messages.append({
                        "role": "tool",
                        "content": f"[Previous result from {entry['name']}: {self._one_line_summary(entry['content'])}]",
                        "tool_use_id": entry["tool_use_id"]
                    })

        return messages

    def _one_line_summary(self, content: str) -> str:
        """Extract first line or key result from tool output."""
        if isinstance(content, dict):
            # For structured results, return just the status/key fields
            return str({k: v for k, v in content.items() if k in ("status", "count", "success")})
        return content.split("\n")[0][:100]
```

### 6.3 Upstream State Scoping

**Problem:** Each downstream agent receives the full `game_design_v3` object (~4K tokens) even though it only needs specific fields.

**Solution — Field-level state projection:**

```python
# Define what each agent needs from upstream state
AGENT_STATE_REQUIREMENTS: dict[str, list[str]] = {
    "scene_architect_v3": [
        "game_design_v3.template_type",
        "game_design_v3.scenes",
        "game_design_v3.visual_theme",
    ],
    "interaction_designer_v3": [
        "game_design_v3.mechanics",
        "game_design_v3.interaction_patterns",
        "game_design_v3.difficulty_curve",
    ],
    "asset_generator_v3": [
        "game_design_v3.visual_style",
        "game_design_v3.scenes[*].background_description",
        "game_design_v3.asset_manifest",
    ],
    "blueprint_assembler_v3": [
        "game_design_v3.template_type",
        "game_design_v3.scoring_config",
        "game_design_v3.metadata",
    ],
}

def project_upstream_state(full_state: dict, agent_name: str) -> str:
    """Extract only the fields this agent needs from upstream state."""
    requirements = AGENT_STATE_REQUIREMENTS.get(agent_name, [])
    projected = {}
    for field_path in requirements:
        value = _resolve_path(full_state, field_path)
        if value is not None:
            projected[field_path] = value
    return json.dumps(projected, indent=None, separators=(",", ":"))

def _resolve_path(state: dict, path: str) -> any:
    """Resolve a dot-separated path with optional array wildcards."""
    parts = path.split(".")
    current = state
    for part in parts:
        if part.endswith("[*]"):
            key = part[:-3]
            current = current.get(key, [])
            # For wildcard arrays, extract the next field from each element
            continue
        if isinstance(current, list):
            current = [item.get(part) for item in current if isinstance(item, dict)]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
```

### 6.4 Dynamic Mechanic Encyclopedia Scoping

**Problem:** System prompts contain a static "mechanic encyclopedia" (~1-2K tokens) covering all 10 mechanic types, even when the game only uses 2.

**Solution:**
```python
# Full encyclopedia definitions (stored separately, not in prompt)
MECHANIC_ENCYCLOPEDIA: dict[str, str] = {
    "DRAG_AND_DROP": "Players drag labels to matching zones...(200 tokens)",
    "SEQUENCE_ORDERING": "Players arrange items in correct order...(200 tokens)",
    "MULTIPLE_CHOICE": "Players select from presented options...(200 tokens)",
    "TRACE_PATH": "Players draw paths between connected points...(200 tokens)",
    "HOTSPOT_CLICK": "Players click on specific regions...(200 tokens)",
    # ... 10 total
}

def build_scoped_system_prompt(
    base_prompt: str,
    game_plan: dict,
) -> str:
    """Build system prompt with only relevant mechanic definitions."""
    active_mechanics = set()
    for scene in game_plan.get("scene_breakdown", []):
        active_mechanics.update(scene.get("mechanics", []))

    # Sort for deterministic caching
    sorted_mechanics = sorted(active_mechanics)

    scoped_definitions = "\n".join(
        f"- {m}: {MECHANIC_ENCYCLOPEDIA[m]}"
        for m in sorted_mechanics
        if m in MECHANIC_ENCYCLOPEDIA
    )

    return f"{base_prompt}\n\n## Active Mechanics\n{scoped_definitions}"
```

---

## 7. Token Savings Estimates

Based on a 54,000 token baseline per pipeline run:

| Technique | Tokens Saved | % Reduction | Confidence | Notes |
|-----------|-------------|-------------|------------|-------|
| **Prompt Caching (system + tools)** | Cost reduction, not token reduction | 45-80% cost savings on cached prefix (~27K static tokens) | Very High | No code changes needed beyond prompt restructuring |
| **Observation Masking** | 8,000 - 10,000 | 15-19% | Very High | Keep last 2 tool results, mask earlier ones |
| **State Projection** | 8,000 - 10,000 | 15-19% | High | Project only needed fields per agent |
| **Tool Schema Minimization** | 2,000 - 3,000 | 4-6% | High | Shorten descriptions, remove unused params |
| **Dynamic System Prompt Scoping** | 4,000 - 8,000 | 7-15% | High | Scope mechanic encyclopedia to active mechanics |
| **Compact Serialization (TOON)** | 3,000 - 4,000 | 6-7% | Medium | Apply to tabular state data |
| **Context Deduplication** | 3,000 - 5,000 | 6-9% | High | Remove overlapping contextvars/prompt data |
| **Retry Overhead Reduction** | 3,000 - 7,000 | 6-13% | Medium | Summarize failed attempts rather than replaying |
| **Hierarchical Sub-Agents** | 2,000 - 4,000 | 4-7% | Medium | Split large agents, requires architecture change |
| **Model Routing** | Cost reduction, not token reduction | 25-35% cost savings | High | Use Haiku for simple sub-tasks |

### Combined Savings Estimate

Techniques are not fully additive (some overlap). Realistic combined savings:

| Scenario | Token Reduction | Cost Reduction | Effort |
|----------|----------------|----------------|--------|
| **Quick Wins Only** (caching + masking + schema minimization) | ~12K tokens (22%) | 55-70% cost | 1-2 days |
| **Medium Investment** (+ state projection + dedup + scoping) | ~25K tokens (46%) | 65-80% cost | 1-2 weeks |
| **Full Optimization** (all techniques) | ~32K tokens (59%) | 75-90% cost | 3-4 weeks |

**Projected token usage after full optimization:** 54K -> ~22K tokens per pipeline run.
**Projected cost after full optimization (including caching + routing):** 80-90% reduction from current baseline.

---

## 8. Priority Implementation Order

Ranked by (estimated savings multiplied by ease of implementation), highest priority first:

### Priority 1: Prompt Caching Structure (Effort: 1 day, Impact: 45-80% cost reduction)

Restructure all agent prompts to maximize cache hits:
1. Move system prompts to a stable prefix position
2. Place tool definitions immediately after system prompts
3. Put variable content (task prompt, conversation history) at the end
4. Add cache breakpoints after system prompt and after tool definitions
5. Ensure system prompts do not contain dynamic values (timestamps, session IDs)

No token reduction, but the single highest cost reduction technique.

### Priority 2: Observation Masking in ReAct Base (Effort: 2 days, Impact: ~9K tokens)

Modify the ReAct base class to mask old tool results:
1. Keep only the last 2 tool results in full
2. Replace earlier tool results with one-line summaries
3. Always preserve the agent's reasoning (assistant messages) in full
4. Use deterministic summary extraction (first line, key fields) — no LLM call needed

Based on "The Complexity Trap" NeurIPS 2025 paper showing this matches LLM summarization quality.

### Priority 3: State Projection (Effort: 3 days, Impact: ~9K tokens)

Define per-agent field requirements and project state:
1. Audit each agent to identify which upstream fields it actually reads
2. Create `AGENT_STATE_REQUIREMENTS` mapping
3. Implement `project_upstream_state()` utility
4. Replace full state serialization in task prompts with projected state
5. Use compact JSON (no whitespace, short separators)

### Priority 4: Context Deduplication (Effort: 2 days, Impact: ~4K tokens)

Audit and eliminate overlapping data between task prompts and tool contextvars:
1. Map which contextvars each tool reads
2. Map which data appears in task prompts
3. Remove redundant context injection from tools — reference task prompt instead
4. Create a `ContextRegistry` to prevent duplicate injection

### Priority 5: Tool Schema Minimization (Effort: 1 day, Impact: ~2.5K tokens)

Reduce verbosity of tool definitions:
1. Shorten all tool descriptions to 1-2 sentences
2. Use minimal parameter descriptions (type + key constraint only)
3. Remove default value descriptions (the default itself is sufficient)
4. Consider lazy tool loading for agents with 4+ tools

### Priority 6: Dynamic System Prompt Scoping (Effort: 2 days, Impact: ~6K tokens)

Scope mechanic encyclopedias to active mechanics:
1. Extract mechanic definitions into a separate registry
2. Build system prompts dynamically based on `game_plan.mechanics`
3. Sort mechanics deterministically to maintain cache hit rates
4. Pre-compute and cache the most common mechanic combinations

### Priority 7: Compact Serialization (Effort: 2 days, Impact: ~3.5K tokens)

Switch structured data to compact formats:
1. Use `json.dumps(data, separators=(",", ":"))` (no whitespace) as a quick win
2. For tabular data (zones, labels, scenes), use CSV-like or TOON format
3. For nested objects, flatten to dot-notation paths where possible

### Priority 8: Model Routing (Effort: 3 days, Impact: 25-35% cost reduction)

Route simple sub-tasks to cheaper models:
1. Identify which agent calls are simple enough for Haiku/GPT-4o-mini
2. Implement a routing layer that selects model based on task type
3. Use larger models for: design reasoning, complex interaction patterns
4. Use smaller models for: validation, classification, schema extraction

### Priority 9: Retry Overhead Reduction (Effort: 2 days, Impact: ~5K tokens)

Optimize how retry attempts accumulate in context:
1. On retry, summarize the failed attempt (reason + what was tried) in 1-2 sentences
2. Do not replay the full failed conversation history
3. Inject only the error message and corrective guidance
4. Cap retry history at 2 summarized attempts before escalating

### Priority 10: Sub-Agent Decomposition (Effort: 1-2 weeks, Impact: ~3K tokens)

Split monolithic agents into focused sub-agents:
1. Identify agents with 5+ tools that handle multiple concerns
2. Split into specialized sub-agents with 2-3 tools each
3. Use a lightweight orchestrator to coordinate sub-agents
4. Each sub-agent carries only its relevant context

---

## 9. Code Patterns

### 9.1 Prompt Caching Setup for Anthropic

```python
from anthropic import Anthropic

client = Anthropic()

def call_agent_with_caching(
    system_prompt: str,
    tool_definitions: list[dict],
    task_prompt: str,
    conversation_history: list[dict],
) -> dict:
    """Call Claude with optimal cache structure."""
    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # Cache breakpoint 1
            }
        ],
        tools=tool_definitions,  # Automatically cached as part of prefix
        messages=[
            # Task prompt (semi-static per pipeline run)
            {"role": "user", "content": [
                {
                    "type": "text",
                    "text": task_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache breakpoint 2
                }
            ]},
            # Conversation history (fully dynamic)
            *conversation_history,
        ],
    )
    return response
```

### 9.2 Observation Masking Implementation

```python
from typing import TypedDict

class ToolResult(TypedDict):
    role: str
    content: str
    tool_use_id: str
    name: str

def mask_old_observations(
    history: list[dict],
    keep_last_n: int = 2,
) -> list[dict]:
    """Mask old tool results, keeping only the last N in full."""
    # Find all tool result indices
    tool_result_indices = [
        i for i, msg in enumerate(history)
        if msg.get("role") == "tool"
    ]

    # Determine which to mask
    mask_before = len(tool_result_indices) - keep_last_n
    indices_to_mask = set(tool_result_indices[:max(0, mask_before)])

    masked_history = []
    for i, msg in enumerate(history):
        if i in indices_to_mask:
            # Replace full tool result with compact summary
            content = msg.get("content", "")
            summary = _extract_summary(content, msg.get("name", "tool"))
            masked_history.append({
                "role": "tool",
                "content": summary,
                "tool_use_id": msg.get("tool_use_id", ""),
            })
        else:
            masked_history.append(msg)

    return masked_history

def _extract_summary(content: str, tool_name: str) -> str:
    """Extract a one-line summary from tool output."""
    if not content:
        return f"[{tool_name}: empty result]"

    # Try to parse as JSON and extract key fields
    try:
        import json
        data = json.loads(content)
        if isinstance(data, dict):
            # Extract status/count/success fields
            key_fields = {
                k: v for k, v in data.items()
                if k in ("status", "success", "count", "error", "total", "result")
            }
            if key_fields:
                return f"[{tool_name}: {json.dumps(key_fields, separators=(',', ':'))}]"
            # Fallback: first 3 keys
            preview = {k: str(v)[:50] for k, v in list(data.items())[:3]}
            return f"[{tool_name}: {json.dumps(preview, separators=(',', ':'))}]"
        elif isinstance(data, list):
            return f"[{tool_name}: list of {len(data)} items]"
    except (json.JSONDecodeError, TypeError):
        pass

    # Plain text: first line, truncated
    first_line = content.split("\n")[0][:120]
    return f"[{tool_name}: {first_line}]"
```

### 9.3 State Projection with Compact Serialization

```python
import json
from typing import Any

# Agent-specific field requirements
AGENT_STATE_REQUIREMENTS: dict[str, list[str]] = {
    "game_designer": [],  # First agent, no upstream state
    "scene_architect": [
        "game_design.template_type",
        "game_design.scenes",
        "game_design.visual_theme",
        "game_design.learning_objectives",
    ],
    "interaction_designer": [
        "game_design.mechanics",
        "game_design.interaction_patterns",
        "scene_specs.scenes",  # Just scene structure, not full detail
    ],
    "asset_generator": [
        "game_design.visual_style",
        "scene_specs.asset_requirements",
        "interaction_spec.zone_definitions",
    ],
    "blueprint_assembler": [
        "game_design.template_type",
        "game_design.scoring_config",
        "scene_specs.scene_count",
        "interaction_spec.mechanic_configs",
        "asset_manifest.assets",
    ],
}

def build_projected_context(state: dict, agent_name: str) -> str:
    """Build compact, projected state context for an agent."""
    requirements = AGENT_STATE_REQUIREMENTS.get(agent_name, [])
    if not requirements:
        return ""

    projected = {}
    for field_path in requirements:
        value = _resolve_nested_path(state, field_path)
        if value is not None:
            projected[field_path] = value

    # Compact JSON: no whitespace
    return json.dumps(projected, separators=(",", ":"), default=str)

def _resolve_nested_path(state: dict, path: str) -> Any:
    """Resolve dot-separated path in nested dict."""
    parts = path.split(".")
    current = state
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current
```

### 9.4 LangGraph pre_model_hook for Token Management

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import trim_messages
from langchain_core.messages.utils import count_tokens_approximately

def create_token_managed_agent(
    model,
    tools,
    system_prompt: str,
    max_context_tokens: int = 8000,
    keep_last_n_results: int = 2,
):
    """Create a ReAct agent with automatic context management."""

    def pre_model_hook(state):
        """Manage message history before each LLM call."""
        messages = state["messages"]

        # Step 1: Mask old tool results
        messages = mask_old_observations(messages, keep_last_n=keep_last_n_results)

        # Step 2: Trim to token budget
        messages = trim_messages(
            messages,
            max_tokens=max_context_tokens,
            strategy="last",
            token_counter=count_tokens_approximately,
            include_system=True,
        )

        return {"messages": messages}

    return create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
        pre_model_hook=pre_model_hook,
    )
```

### 9.5 Context Registry for Deduplication

```python
from contextvars import ContextVar
from typing import Set

# Registry of what data is already in the agent's context
_context_registry: ContextVar[Set[str]] = ContextVar(
    "context_registry", default=set()
)

def register_context(key: str) -> None:
    """Mark a piece of context as already present in the agent's prompt."""
    registry = _context_registry.get()
    registry.add(key)
    _context_registry.set(registry)

def is_in_context(key: str) -> bool:
    """Check if data is already in the agent's prompt context."""
    return key in _context_registry.get()

def clear_context_registry() -> None:
    """Clear the registry at the start of each agent call."""
    _context_registry.set(set())

# Usage in tool implementation:
class DomainKnowledgeTool:
    def execute(self, query: str) -> str:
        knowledge = self._retrieve(query)

        if is_in_context("domain_knowledge"):
            # Data already in task prompt, return only analysis
            return f"Analysis based on provided domain context: {self._analyze(knowledge)}"
        else:
            # Data not yet in context, include it
            register_context("domain_knowledge")
            return f"Domain Knowledge:\n{knowledge}\n\nAnalysis: {self._analyze(knowledge)}"
```

---

## 10. Sources

### Academic Papers

1. [ACON: Optimizing Context Compression for Long-horizon LLM Agents](https://arxiv.org/abs/2510.00615) — Kang et al., arXiv, October 2025
2. [AgentFold: Long-Horizon Web Agents with Proactive Context Management](https://arxiv.org/abs/2510.24699) — Tongji Lab / Alibaba, October 2025
3. [PAACE: Plan-Aware Automated Agent Context Engineering Framework](https://arxiv.org/abs/2512.16970) — arXiv, December 2025
4. [U-Fold: Dynamic Intent-Aware Context Folding for User-Centric Agents](https://arxiv.org/abs/2601.18285) — Su et al., January 2026
5. [Active Context Compression: Autonomous Memory Management in LLM Agents](https://arxiv.org/abs/2601.07190) — arXiv, January 2026
6. [Cut the Crap / AgentPrune: An Economical Communication Pipeline for LLM-based Multi-Agent Systems](https://arxiv.org/abs/2410.02506) — Yue et al., ICLR 2025
7. [AgentDropout: Dynamic Agent Elimination for Token-Efficient Multi-Agent Collaboration](https://aclanthology.org/2025.acl-long.1170/) — Wang et al., ACL 2025
8. [The Complexity Trap: Simple Observation Masking Is as Efficient as LLM Summarization for Agent Context Management](https://arxiv.org/abs/2508.21433) — Lindenbauer et al., JetBrains Research, NeurIPS 2025 (DL4Code)
9. [LLMLingua: Compressing Prompts for Accelerated Inference of LLMs](https://arxiv.org/abs/2310.05736) — Microsoft Research, EMNLP 2023
10. [Selective Context: Compressing Context to Enhance Inference Efficiency](https://aclanthology.org/2023.emnlp-main.391/) — Li et al., EMNLP 2023
11. [In-Context Autoencoder (ICAE) for Context Compression](https://arxiv.org/abs/2307.06945) — ICLR 2024
12. [Prompt Compression for Large Language Models: A Survey](https://aclanthology.org/2025.naacl-long.368/) — Li et al., NAACL 2025 (Oral)
13. [SimpleMem: Efficient Lifelong Memory for LLM Agents](https://arxiv.org/abs/2601.02553) — UNC Chapel Hill, January 2026
14. [Don't Break the Cache: An Evaluation of Prompt Caching for Long-Horizon Agentic Tasks](https://arxiv.org/abs/2601.06007) — arXiv, January 2026

### Provider Documentation

15. [Anthropic Prompt Caching Documentation](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)
16. [Anthropic Token-Efficient Tool Use (Beta)](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/token-efficient-tool-use)
17. [Anthropic Token-Saving Updates](https://www.anthropic.com/news/token-saving-updates)
18. [OpenAI Prompt Caching Guide](https://platform.openai.com/docs/guides/prompt-caching)
19. [Google Gemini API Pricing (Context Caching)](https://ai.google.dev/gemini-api/docs/pricing)
20. [Google ADK Context Compaction](https://google.github.io/adk-docs/context/compaction/)

### Framework Documentation & Blog Posts

21. [LangGraph: How to Manage Conversation History in a ReAct Agent](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent-manage-message-history/)
22. [LangChain Context Management for Deep Agents](https://blog.langchain.com/context-management-for-deepagents/)
23. [LangChain Context Engineering for Agents](https://blog.langchain.com/context-engineering-for-agents/)
24. [LangChain Context Engineering Documentation](https://docs.langchain.com/oss/python/langchain/context-engineering)
25. [CrewAI Agent Documentation](https://docs.crewai.com/en/concepts/agents)

### Industry Blog Posts & Guides

26. [Speakeasy: Reducing MCP Token Usage by 100x with Dynamic Toolsets](https://www.speakeasy.com/blog/how-we-reduced-token-usage-by-100x-dynamic-toolsets-v2)
27. [Factory.ai: Evaluating Context Compression for AI Agents](https://factory.ai/news/evaluating-compression)
28. [Factory.ai: Compressing Context](https://factory.ai/news/compressing-context)
29. [JetBrains Research: Cutting Through the Noise: Smarter Context Management](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)
30. [Elementor: Token Optimization Strategies for AI Agents](https://medium.com/elementor-engineers/optimizing-token-usage-in-agent-based-assistants-ffd1822ece9c)
31. [KV-Cache Aware Prompt Engineering: How Stable Prefixes Unlock 65% Latency Improvements](https://ankitbko.github.io/blog/2025/08/prompt-engineering-kv-cache/)
32. [ngrok: Prompt Caching: 10x Cheaper LLM Tokens, But How?](https://ngrok.com/blog/prompt-caching/)
33. [Prompt Caching Guide 2025: Lower AI Costs](https://promptbuilder.cc/blog/prompt-caching-token-economics-2025)
34. [From JSON to TOON: Evolving Serialization for LLMs](https://pub.towardsai.net/from-json-to-toon-evolving-serialization-for-llms-60e99076f48c)
35. [TOON Format GitHub Repository](https://github.com/toon-format/toon)
36. [MCP Token Bloat Mitigation Proposal (SEP-1576)](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1576)
37. [Phil Schmid: Context Engineering for AI Agents Part 2](https://www.philschmid.de/context-engineering-part-2)
38. [Managing Operational Costs of Agents Using LLMs](https://apxml.com/courses/multi-agent-llm-systems-design-implementation/chapter-6-system-evaluation-debugging-tuning/managing-llm-agent-costs)

### GitHub Repositories

39. [Microsoft LLMLingua](https://github.com/microsoft/LLMLingua)
40. [JetBrains The Complexity Trap](https://github.com/JetBrains-Research/the-complexity-trap)
41. [AgentPrune](https://github.com/yanweiyue/AgentPrune)
42. [AgentDropout](https://github.com/wangzx1219/AgentDropout)
43. [SimpleMem](https://github.com/aiming-lab/SimpleMem)
44. [LangChain Deep Agents](https://github.com/langchain-ai/deepagents)
45. [Prompt Compression Survey Resources](https://github.com/ZongqianLi/Prompt-Compression-Survey)
46. [Selective Context](https://github.com/liyucheng09/Selective_Context)

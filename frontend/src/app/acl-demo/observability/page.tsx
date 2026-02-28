'use client';

import Link from 'next/link';
import React, { useState } from 'react';

/* ═══════════════════════════════════════════════════════════════
   HARDCODED OBSERVABILITY DASHBOARD — light theme, for demo screenshots
   ═══════════════════════════════════════════════════════════════ */

const STAGES = [
  { id: 'input_analyzer', label: 'Input Analyzer', phase: 0, type: 'llm', tokens: 1240, cost: 0.031, time: 3.2, status: 'success' },
  { id: 'dk_retriever', label: 'DK Retriever', phase: 0, type: 'llm', tokens: 2180, cost: 0.054, time: 4.1, status: 'success' },
  { id: 'game_concept_designer', label: 'Concept Designer', phase: 1, type: 'llm', tokens: 4820, cost: 0.121, time: 8.7, status: 'success' },
  { id: 'concept_validator', label: 'QG1: Concept', phase: 1, type: 'qg', tokens: 0, cost: 0, time: 0.1, status: 'success' },
  { id: 'game_plan_builder', label: 'Plan Builder', phase: 2, type: 'deterministic', tokens: 0, cost: 0, time: 0.3, status: 'success' },
  { id: 'plan_validator', label: 'QG2: Plan', phase: 2, type: 'qg', tokens: 0, cost: 0, time: 0.1, status: 'success' },
  { id: 'content_dispatch', label: 'Content Dispatch', phase: 3, type: 'router', tokens: 0, cost: 0, time: 0.1, status: 'success' },
  { id: 'content_gen_1', label: 'Content Gen (S1)', phase: 3, type: 'parallel', tokens: 3100, cost: 0.078, time: 6.4, status: 'success' },
  { id: 'content_gen_2', label: 'Content Gen (S2)', phase: 3, type: 'parallel', tokens: 2890, cost: 0.072, time: 5.9, status: 'success' },
  { id: 'content_gen_3', label: 'Content Gen (S3)', phase: 3, type: 'parallel', tokens: 3210, cost: 0.080, time: 6.8, status: 'success' },
  { id: 'content_merge', label: 'Content Merge', phase: 3, type: 'deterministic', tokens: 0, cost: 0, time: 0.2, status: 'success' },
  { id: 'content_validator', label: 'QG3: Content', phase: 3, type: 'qg', tokens: 0, cost: 0, time: 0.4, status: 'success' },
  { id: 'asset_dispatch', label: 'Asset Dispatch', phase: 4, type: 'router', tokens: 0, cost: 0, time: 0.1, status: 'success' },
  { id: 'asset_worker_1', label: 'Asset Worker (S1)', phase: 4, type: 'parallel', tokens: 890, cost: 0.022, time: 3.1, status: 'success' },
  { id: 'asset_worker_2', label: 'Asset Worker (S2)', phase: 4, type: 'parallel', tokens: 760, cost: 0.019, time: 2.8, status: 'success' },
  { id: 'asset_merge', label: 'Asset Merge', phase: 4, type: 'deterministic', tokens: 0, cost: 0, time: 0.1, status: 'success' },
  { id: 'blueprint_assembler', label: 'Blueprint Assembler', phase: 5, type: 'deterministic', tokens: 0, cost: 0, time: 0.5, status: 'success' },
  { id: 'blueprint_validator', label: 'QG4: Blueprint', phase: 5, type: 'qg', tokens: 0, cost: 0, time: 0.2, status: 'success' },
];

const TOTAL_TOKENS = STAGES.reduce((s, st) => s + st.tokens, 0);
const TOTAL_COST = STAGES.reduce((s, st) => s + st.cost, 0);
const TOTAL_TIME = 47;

const PHASE_LABELS = ['Context Gathering', 'Concept Design', 'Game Plan', 'Scene Content', 'Assets', 'Assembly'];
const PHASE_BG = ['bg-indigo-50', 'bg-violet-50', 'bg-emerald-50', 'bg-amber-50', 'bg-pink-50', 'bg-green-50'];

const TYPE_BADGES: Record<string, { label: string; cls: string }> = {
  llm:           { label: 'LLM',     cls: 'bg-blue-100 text-blue-700' },
  deterministic: { label: 'Determ.', cls: 'bg-green-100 text-green-700' },
  qg:            { label: 'No LLM',  cls: 'bg-red-100 text-red-600' },
  parallel:      { label: '×N',      cls: 'bg-purple-100 text-purple-700' },
  router:        { label: 'Router',  cls: 'bg-gray-100 text-gray-500' },
};

const NODE_STYLES: Record<string, string> = {
  llm:           'border-blue-300 bg-blue-50 hover:bg-blue-100',
  deterministic: 'border-green-300 bg-green-50 hover:bg-green-100',
  qg:            'border-red-300 bg-red-50 hover:bg-red-100',
  parallel:      'border-purple-300 bg-purple-50 hover:bg-purple-100',
  router:        'border-gray-300 bg-gray-50 hover:bg-gray-100',
};

const NODE_TEXT: Record<string, string> = {
  llm: 'text-blue-800', deterministic: 'text-green-800', qg: 'text-red-800',
  parallel: 'text-purple-800', router: 'text-gray-700',
};

// QG3 inspector detail
const QG3_DETAIL = {
  scenes_validated: 3,
  schema_compliance: '100%',
  duration_ms: 412,
  predicates: [
    { pred: 'bloom(g) = bloom(b)', detail: 'Level: Apply', pass: true },
    { pred: 'op_count ≥ τ', detail: 'Count: 12 ≥ 5', pass: true },
    { pred: 'feedback ⊨ Bloom', detail: 'Feedback aligned', pass: true },
  ],
};

const BLUEPRINT_DETAIL = {
  templateType: 'interactive_diagram',
  title: 'Label the Parts of a Plant Cell',
  mechanic: 'drag_drop',
  domain: 'biology',
  educationLevel: 'k12',
  bloomsLevel: 'Remember',
  scenes: [
    { id: 'scene_1', title: 'Cell Wall & Membrane', zones: 4, labels: 4 },
    { id: 'scene_2', title: 'Organelles', zones: 5, labels: 5 },
    { id: 'scene_3', title: 'Full Cell Review', zones: 9, labels: 9 },
  ],
  scoreContracts: { scene_1: 100, scene_2: 125, scene_3: 225 },
  totalScore: 450,
  generation_complete: true,
  is_degraded: false,
};

export default function ObservabilityPage() {
  const [selectedStage, setSelectedStage] = useState<string>('content_validator');
  const selected = STAGES.find(s => s.id === selectedStage);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {/* ══════ Top bar ══════ */}
      <header className="border-b border-gray-200 bg-white px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <Link href="/acl-demo" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
            ← Back
          </Link>
          <h1 className="text-lg font-bold text-gray-900">Pipeline Run</h1>
          <span className="text-xs bg-green-100 text-green-700 px-2.5 py-0.5 rounded-full font-medium border border-green-200">
            ● Completed
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <div className="text-gray-500">
            Query: <span className="text-gray-900 font-medium">&quot;Label the parts of a plant cell and identify their functions&quot;</span>
          </div>
          <div className="flex items-center gap-4 text-gray-500">
            <span>Tokens: <span className="text-gray-900 font-mono font-semibold">{TOTAL_TOKENS.toLocaleString()}</span></span>
            <span>Cost: <span className="text-emerald-600 font-mono font-semibold">${TOTAL_COST.toFixed(2)}</span></span>
            <span>Time: <span className="text-gray-900 font-mono font-semibold">{TOTAL_TIME}s</span></span>
          </div>
          <Link
            href="/acl-demo/play/bio-k12-plant-cell-drag-drop"
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-violet-600 text-white text-sm font-semibold rounded-lg hover:from-blue-700 hover:to-violet-700 shadow-md hover:shadow-lg transition-all flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Play Game
          </Link>
        </div>
      </header>

      <div className="flex h-[calc(100vh-57px)]">
        {/* ══════ LEFT: DAG Graph ══════ */}
        <div className="flex-1 p-6 overflow-auto">
          <div className="flex gap-3 min-w-[900px]">
            {PHASE_LABELS.map((phase, pi) => {
              const phaseStages = STAGES.filter(s => s.phase === pi);
              return (
                <div key={pi} className="flex-1 min-w-0">
                  {/* Phase header */}
                  <div className="text-center mb-3">
                    <div className="text-[10px] text-gray-400 uppercase tracking-wider font-medium">Phase {pi}</div>
                    <div className="text-xs font-semibold text-gray-700">{phase}</div>
                  </div>
                  {/* Phase column */}
                  <div className={`rounded-xl p-2.5 space-y-2 min-h-[250px] ${PHASE_BG[pi]}`}>
                    {phaseStages.map(stage => {
                      const isSelected = stage.id === selectedStage;
                      return (
                        <button
                          key={stage.id}
                          onClick={() => setSelectedStage(stage.id)}
                          className={`w-full text-left rounded-lg border p-2.5 transition-all cursor-pointer shadow-sm ${
                            isSelected
                              ? 'ring-2 ring-blue-500 border-blue-400 bg-white shadow-md'
                              : `${NODE_STYLES[stage.type]}`
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className={`text-xs font-semibold ${isSelected ? 'text-blue-700' : NODE_TEXT[stage.type]}`}>
                              {stage.label}
                            </span>
                            <span className="w-2.5 h-2.5 rounded-full bg-green-500 border border-green-600 flex-shrink-0" />
                          </div>
                          <div className="flex items-center justify-between mt-1.5">
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${TYPE_BADGES[stage.type].cls}`}>
                              {TYPE_BADGES[stage.type].label}
                            </span>
                            {stage.tokens > 0 && (
                              <span className="text-[9px] font-mono text-gray-400">
                                {(stage.tokens / 1000).toFixed(1)}k
                              </span>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ══════ RIGHT: Stage Inspector ══════ */}
        <div className="w-[380px] border-l border-gray-200 bg-white overflow-y-auto shadow-inner">
          {selected && (
            <div className="p-5">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-sm font-bold text-gray-900">{selected.label}</h2>
                  <p className="text-[10px] text-gray-400 font-mono mt-0.5">{selected.id}</p>
                </div>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium border border-green-200">
                  ✓ Success
                </span>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
                  <div className="text-[9px] text-gray-400 uppercase font-medium">Tokens</div>
                  <div className="text-sm font-mono font-bold text-gray-900">{selected.tokens.toLocaleString()}</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
                  <div className="text-[9px] text-gray-400 uppercase font-medium">Cost</div>
                  <div className="text-sm font-mono font-bold text-emerald-600">${selected.cost.toFixed(3)}</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
                  <div className="text-[9px] text-gray-400 uppercase font-medium">Time</div>
                  <div className="text-sm font-mono font-bold text-gray-900">{selected.time}s</div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 mb-4 border-b border-gray-200 pb-2">
                {['Output', 'Input', 'Logs'].map((tab, i) => (
                  <button
                    key={tab}
                    className={`text-[11px] px-3 py-1 rounded font-medium transition-colors ${
                      i === 0
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* ── QG3: Content Validator ── */}
              {selectedStage === 'content_validator' && (
                <div className="space-y-3">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-green-600 text-base font-bold">✓</span>
                      <span className="text-sm font-bold text-green-800">Validation: PASSED</span>
                    </div>
                    <div className="text-xs text-green-700">
                      All {QG3_DETAIL.scenes_validated} scenes validated · Schema compliance: {QG3_DETAIL.schema_compliance}
                    </div>
                  </div>

                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">FOL Predicates</div>
                  {QG3_DETAIL.predicates.map((p, i) => (
                    <div key={i} className="bg-gray-50 border border-gray-200 rounded-lg p-2.5 flex items-center justify-between">
                      <div>
                        <code className="text-[11px] text-amber-700 font-semibold">{p.pred}</code>
                        <div className="text-[9px] text-gray-400 mt-0.5">{p.detail}</div>
                      </div>
                      <span className="text-green-600 text-xs font-bold">✓</span>
                    </div>
                  ))}

                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-2">Duration</div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-2.5 text-xs font-mono text-gray-600">
                    {QG3_DETAIL.duration_ms}ms — deterministic, zero LLM inference
                  </div>
                </div>
              )}

              {/* ── Blueprint Assembler ── */}
              {selectedStage === 'blueprint_assembler' && (
                <div className="space-y-3">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-green-600 text-base font-bold">✓</span>
                      <span className="text-sm font-bold text-green-800">Blueprint Assembled</span>
                    </div>
                    <div className="text-xs text-green-700">
                      generation_complete: true · is_degraded: false
                    </div>
                  </div>

                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Blueprint JSON</div>
                  <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-[10px] font-mono text-gray-700 overflow-x-auto leading-relaxed">
{JSON.stringify(BLUEPRINT_DETAIL, null, 2)}
                  </pre>
                </div>
              )}

              {/* ── Generic stage ── */}
              {selectedStage !== 'content_validator' && selectedStage !== 'blueprint_assembler' && (
                <div className="space-y-3">
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-green-600 font-bold">✓</span>
                      <span className="text-sm font-semibold text-gray-800">{selected.label} — Completed</span>
                    </div>
                    <div className="text-xs text-gray-500 space-y-1">
                      <div>Type: <span className="text-gray-800 font-medium">{selected.type}</span></div>
                      <div>Phase: <span className="text-gray-800 font-medium">{selected.phase} — {PHASE_LABELS[selected.phase]}</span></div>
                      {selected.tokens > 0 && (
                        <div>Tokens: <span className="text-gray-800 font-mono">{selected.tokens.toLocaleString()}</span></div>
                      )}
                      <div>Duration: <span className="text-gray-800 font-mono">{selected.time}s</span></div>
                    </div>
                  </div>

                  {selected.type === 'llm' && (
                    <>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Model</div>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800">
                        gemini-2.5-pro · Temperature: 0.7
                      </div>
                    </>
                  )}

                  {selected.type === 'qg' && (
                    <>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Validation</div>
                      <div className="bg-green-50 border border-green-200 rounded-lg p-2.5 text-xs text-green-800">
                        ✓ PASSED — Deterministic, no LLM inference
                      </div>
                    </>
                  )}

                  {selected.type === 'parallel' && (
                    <>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Parallel Execution</div>
                      <div className="bg-purple-50 border border-purple-200 rounded-lg p-2.5 text-xs text-purple-800">
                        Dispatched via LangGraph Send() API
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

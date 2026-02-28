'use client'

/* ─────────────────────────────────────────────────────────────
   V4 Pipeline DAG — Pure CSS diagram (no ReactFlow)
   Clean, readable pipeline visualization for the landing page.
   ───────────────────────────────────────────────────────────── */

/* ── Node badge component ─── */
function Badge({ kind, children }: { kind: 'ai' | 'valid' | 'merge' | 'determ'; children: React.ReactNode }) {
  const styles = {
    ai:     { bg: 'bg-violet-100 dark:bg-violet-900/30', border: 'border-violet-300 dark:border-violet-700', badge: 'bg-violet-500', label: 'AI' },
    valid:  { bg: 'bg-emerald-100 dark:bg-emerald-900/30', border: 'border-emerald-300 dark:border-emerald-700', badge: 'bg-emerald-500', label: 'V' },
    merge:  { bg: 'bg-sky-100 dark:bg-sky-900/30', border: 'border-sky-300 dark:border-sky-700', badge: 'bg-sky-500', label: 'M' },
    determ: { bg: 'bg-slate-100 dark:bg-slate-900/30', border: 'border-slate-300 dark:border-slate-700', badge: 'bg-slate-500', label: 'D' },
  }
  const s = styles[kind]
  return (
    <div className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border ${s.bg} ${s.border} shadow-sm`}>
      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0 ${s.badge}`}>
        {s.label}
      </span>
      <span className="text-[12px] font-semibold text-foreground whitespace-nowrap">{children}</span>
    </div>
  )
}

/* ── Send fanout badge ─── */
function Fanout({ label, count }: { label: string; count?: string }) {
  return (
    <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 border border-violet-200 dark:border-violet-800">
      Send ×{count ?? 'N'} ({label})
    </span>
  )
}

/* ── Retry loop badge ─── */
function RetryBadge() {
  return (
    <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800 flex items-center gap-1">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0">
        <path d="M8 5a3 3 0 1 1-.9-2.1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        <path d="M8 1v2H6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      retry
    </span>
  )
}

/* ── Auto-repair badge ─── */
function RepairBadge() {
  return (
    <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800 flex items-center gap-1">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0">
        <path d="M7.5 2.5L5 5 2.5 7.5M5 5l2.5 2.5M5 5L2.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
      auto-repair
    </span>
  )
}

/* ── Vertical connector ─── */
function Connector({ short }: { short?: boolean }) {
  return (
    <div className="flex justify-center">
      <div className={`w-px ${short ? 'h-3' : 'h-5'} bg-border dark:bg-slate-700`} />
    </div>
  )
}

/* ── Arrow down icon ─── */
function ArrowDown() {
  return (
    <div className="flex justify-center -my-0.5">
      <svg width="12" height="16" viewBox="0 0 12 16" className="text-slate-400 dark:text-slate-600">
        <path d="M6 0v12M2 9l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

/* ── Horizontal arrow between nodes ─── */
function HArrow() {
  return (
    <div className="flex items-center px-1">
      <svg width="24" height="12" viewBox="0 0 24 12" className="text-slate-400 dark:text-slate-600 shrink-0">
        <path d="M0 6h18M15 3l4 3-4 3" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

/* ── Phase section wrapper ─── */
function Phase({ label, color, children }: { label: string; color: string; children: React.ReactNode }) {
  return (
    <div className="relative rounded-xl border border-border/50 dark:border-slate-800 bg-card/50 dark:bg-slate-900/30 p-4 pt-3">
      <div
        className="absolute top-0 left-0 w-1 h-full rounded-l-xl"
        style={{ background: color }}
      />
      <div className="text-[10px] font-bold uppercase tracking-[0.15em] mb-3 pl-2" style={{ color }}>
        {label}
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  )
}

/* ── Node row: horizontal layout with optional arrow between nodes ─── */
function Row({ children, center }: { children: React.ReactNode; center?: boolean }) {
  return (
    <div className={`flex items-center gap-2 flex-wrap ${center ? 'justify-center' : 'justify-center'}`}>
      {children}
    </div>
  )
}

/* ── Subtitle text under a node ─── */
function Sub({ children }: { children: React.ReactNode }) {
  return <span className="text-[9px] text-muted-foreground ml-7">{children}</span>
}

/* ── Main component ───────────────────────────────────────── */
export default function V4PipelineDAG() {
  return (
    <div className="w-full max-w-2xl mx-auto space-y-0">
      {/* START */}
      <div className="flex justify-center">
        <div className="px-5 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/40 border border-blue-300 dark:border-blue-700 text-[12px] font-bold text-blue-700 dark:text-blue-300 tracking-wider">
          START
        </div>
      </div>

      <ArrowDown />

      {/* Phase 0: Context Gathering */}
      <Phase label="Phase 0 — Context Gathering" color="#3b82f6">
        <Row>
          <Badge kind="ai">Input Analyzer</Badge>
          <span className="text-[10px] text-muted-foreground font-medium px-2">parallel</span>
          <Badge kind="ai">DK Retriever</Badge>
        </Row>
        <Connector short />
        <Row center>
          <Badge kind="merge">Phase 0 Merge</Badge>
        </Row>
      </Phase>

      <ArrowDown />

      {/* Phase 1: Game Design */}
      <Phase label="Phase 1 — Game Design" color="#8b5cf6">
        {/* 1a: Concept */}
        <div className="space-y-1">
          <div className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider pl-2">1a. Concept</div>
          <Row>
            <Badge kind="ai">Concept Designer</Badge>
            <HArrow />
            <Badge kind="valid">Concept Validator</Badge>
            <RetryBadge />
          </Row>
        </div>

        <Connector short />

        {/* 1b: Scenes */}
        <div className="space-y-1">
          <div className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider pl-2">1b. Scene Planning</div>
          <Row>
            <div className="space-y-1">
              <Badge kind="ai">Scene Designer</Badge>
              <div className="flex justify-center"><Fanout label="per scene" count="S" /></div>
            </div>
            <HArrow />
            <Badge kind="merge">Scene Design Merge</Badge>
            <HArrow />
            <Badge kind="valid">Scene Validator</Badge>
            <RetryBadge />
          </Row>

          <Connector short />

          <Row>
            <Badge kind="determ">Graph Builder</Badge>
            <HArrow />
            <Badge kind="valid">Plan Validator</Badge>
            <RetryBadge />
          </Row>
        </div>
      </Phase>

      <ArrowDown />

      {/* Phase 2: Scene Content Generation */}
      <Phase label="Phase 2 — Scene Content Generation" color="#ec4899">
        {/* 2a: Content */}
        <div className="space-y-1">
          <div className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider pl-2">2a. Content</div>
          <Row center>
            <div className="space-y-1 flex flex-col items-center">
              <Badge kind="ai">Content Generator</Badge>
              <Fanout label="per task" count="T" />
            </div>
          </Row>
          <Connector short />
          <Row>
            <Badge kind="merge">Content Merge</Badge>
            <HArrow />
            <div className="space-y-0.5">
              <Badge kind="ai">Item Asset Worker</Badge>
              <Sub>sequential, all tasks</Sub>
            </div>
          </Row>
        </div>

        <Connector short />

        {/* 2b: Interactions */}
        <div className="space-y-1">
          <div className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider pl-2">2b. Interactions</div>
          <Row>
            <div className="space-y-1">
              <Badge kind="ai">Interaction Designer</Badge>
              <div className="flex justify-center"><Fanout label="per scene" count="S" /></div>
            </div>
            <HArrow />
            <Badge kind="merge">Interaction Merge</Badge>
          </Row>
        </div>
      </Phase>

      <ArrowDown />

      {/* Phase 3: Assets */}
      <Phase label="Phase 3 — Asset Generation" color="#f97316">
        <Row>
          <div className="space-y-1">
            <Badge kind="ai">Asset Worker</Badge>
            <div className="flex justify-center"><Fanout label="per scene" count="S" /></div>
            <Sub>if diagram needed</Sub>
          </div>
          <HArrow />
          <Badge kind="merge">Asset Merge</Badge>
          <RetryBadge />
        </Row>
      </Phase>

      <ArrowDown />

      {/* Phase 4: Output */}
      <Phase label="Phase 4 — Blueprint Assembly" color="#22c55e">
        <Row>
          <div className="space-y-0.5">
            <Badge kind="determ">Blueprint Assembler</Badge>
            <Sub>final playable JSON</Sub>
          </div>
          <HArrow />
          <div className="space-y-0.5">
            <Badge kind="valid">Blueprint Validator</Badge>
            <RepairBadge />
          </div>
        </Row>
      </Phase>

      <ArrowDown />

      {/* END */}
      <div className="flex justify-center">
        <div className="px-5 py-1.5 rounded-full bg-green-100 dark:bg-green-900/40 border border-green-300 dark:border-green-700 text-[12px] font-bold text-green-700 dark:text-green-300 tracking-wider">
          END
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 justify-center pt-5 flex-wrap">
        {[
          { badge: 'bg-violet-500', label: 'LLM Agent' },
          { badge: 'bg-emerald-500', label: 'Validator' },
          { badge: 'bg-sky-500', label: 'Merge Barrier' },
          { badge: 'bg-slate-500', label: 'Deterministic' },
        ].map(({ badge, label }) => (
          <span key={label} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className={`w-2.5 h-2.5 rounded-full ${badge}`} />
            {label}
          </span>
        ))}
        <RetryBadge />
        <RepairBadge />
        <Fanout label="parallel" count="N" />
      </div>
      <div className="text-center text-[10px] text-muted-foreground pt-1">
        Each game has <span className="font-semibold">S</span> scenes, each consisting of <span className="font-semibold">T</span> tasks
      </div>
    </div>
  )
}

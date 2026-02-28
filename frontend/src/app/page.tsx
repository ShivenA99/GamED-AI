'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { GenerationProgress } from '@/components/pipeline'
import { Button } from '@/components/ui/button'
import V4PipelineDAG from '@/components/V4PipelineDAG'

const PIPELINE_PRESETS = [
  {
    id: 'preset_1',
    name: 'Sequential',
    description: 'Standard pipeline with 17 specialized agents',
    icon: '📊',
    recommended: false,
    features: ['17 sequential agents', 'Full observability', 'Stable baseline'],
  },
  {
    id: 'v3',
    name: 'ReAct Agentic',
    description: '5-phase ReAct pipeline with 12 agents',
    icon: '🚀',
    recommended: false,
    features: ['12 ReAct agents', '22 tools', 'Multi-mechanic support'],
  },
  {
    id: 'v4',
    name: 'Hierarchical Agentic',
    description: 'Streamlined 5-phase pipeline with parallel assets + SAM3',
    icon: '⚡',
    recommended: true,
    features: ['9 agents', 'Parallel asset dispatch', 'SAM3 zone refinement', 'Send API'],
  },
]

const DIAGRAM_QUESTIONS = [
  { text: 'Label the parts of a human heart', icon: '❤️' },
  { text: 'Identify the organelles in an animal cell', icon: '🔬' },
  { text: 'Map the major bones in the skeleton', icon: '🦴' },
  { text: 'Label the layers of the Earth', icon: '🌍' },
  { text: 'Identify parts of a plant cell', icon: '🌱' },
  { text: 'Label the components of the water cycle', icon: '💧' },
]

const ALGORITHM_QUESTIONS = [
  { text: 'Trace through bubble sort on [5, 3, 8, 1, 2]', icon: '🔍' },
  { text: 'Find the bug in this binary search implementation', icon: '🐛' },
  { text: 'Arrange the steps of merge sort in correct order', icon: '🧩' },
  { text: 'Determine the Big-O complexity of nested loops', icon: '📊' },
  { text: 'Solve the 0/1 knapsack problem with 4 items', icon: '🎒' },
  { text: 'Trace BFS traversal on a graph', icon: '🔍' },
]

function AnimatedBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 dark:from-gray-950 dark:via-gray-900 dark:to-gray-900" />
      <div
        className="absolute inset-0 opacity-[0.02] dark:opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(to right, var(--canvas-primary) 1px, transparent 1px),
            linear-gradient(to bottom, var(--canvas-primary) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 0%, rgba(7, 112, 162, 0.05) 0%, transparent 60%)',
        }}
      />
    </div>
  )
}

export default function Home() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [processId, setProcessId] = useState<string | null>(null)
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'generating' | 'success' | 'error'>('idle')
  const [selectedPreset, setSelectedPreset] = useState('v4')
  const [selectedTemplate, setSelectedTemplate] = useState<'interactive_diagram' | 'algorithm_game'>('interactive_diagram')
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null)
  const [expandedStage, setExpandedStage] = useState<string | null>(null)
  const [libraryTab, setLibraryTab] = useState<'diagram' | 'algorithm' | 'engine' | 'pipeline'>('diagram')
  const [techTab, setTechTab] = useState<'architecture' | 'pipeline' | 'dataflow' | 'research'>('architecture')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const router = useRouter()

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
    }
  }, [question])

  // Reset template selection when leaving V4
  useEffect(() => {
    if (selectedPreset !== 'v4') {
      setSelectedTemplate('interactive_diagram')
    }
  }, [selectedPreset])

  const provider = 'google'
  const topology = 'T1'

  const handleGenerate = async () => {
    if (!question.trim()) return

    setLoading(true)
    setGenerationStatus('generating')
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_text: question,
          question_options: null,
          config: {
            provider: provider,
            topology: topology,
            pipeline_preset: selectedPreset === 'v4' && selectedTemplate === 'algorithm_game' ? 'v4_algorithm' : selectedPreset,
          }
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `HTTP ${response.status}: Failed to start generation`)
      }

      const data = await response.json()

      if (data.process_id) {
        setProcessId(data.process_id)
        if (data.run_id) {
          router.push(`/pipeline/runs/${data.run_id}`)
        } else {
          const findRunAndRedirect = async () => {
            try {
              for (let i = 0; i < 10; i++) {
                await new Promise(resolve => setTimeout(resolve, 500))
                const runsResponse = await fetch(`/api/observability/runs?process_id=${data.process_id}`)
                if (runsResponse.ok) {
                  const runsData = await runsResponse.json()
                  if (runsData.runs && runsData.runs.length > 0) {
                    const latestRun = runsData.runs[0]
                    router.push(`/pipeline/runs/${latestRun.id}`)
                    return
                  }
                }
              }
              router.push(`/games`)
            } catch (err) {
              console.error('Error finding run:', err)
              router.push(`/games`)
            }
          }
          findRunAndRedirect()
        }
      } else {
        throw new Error('No process_id returned from server')
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Generation error:', error)
      }
      setGenerationStatus('error')
      setProcessId(null)
      alert(error instanceof Error ? error.message : 'Failed to start generation. Make sure the backend is running.')
      setLoading(false)
    }
  }

  const handleGenerationComplete = (success: boolean) => {
    setLoading(false)
    if (success && processId) {
      setGenerationStatus('success')
      setTimeout(() => {
        router.push(`/game/${processId}`)
      }, 1000)
    } else {
      setGenerationStatus('error')
    }
  }

  const handleCancelGeneration = () => {
    setLoading(false)
    setProcessId(null)
    setGenerationStatus('idle')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleGenerate()
    }
  }

  return (
    <div className="relative min-h-screen">
      <AnimatedBackground />

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">

        {/* ═══════════════ 1. Hero ═══════════════ */}
        <section className="text-center pt-8 pb-6">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-foreground mb-4 leading-tight">
            Transform Questions into
            <span className="block bg-gradient-to-r from-[var(--canvas-primary)] to-[var(--canvas-secondary)] bg-clip-text text-transparent">
              Interactive Learning Games
            </span>
          </h1>
        </section>

        {/* ═══════════════ 2. Chat Interface ═══════════════ */}
        <section className="max-w-3xl mx-auto mb-14">
          <div className="chat-container">
            {processId && generationStatus === 'generating' ? (
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-[var(--canvas-primary)] to-[var(--canvas-secondary)] rounded-xl flex items-center justify-center">
                      <svg className="w-5 h-5 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground">Creating Your Game</h3>
                      <p className="text-sm text-muted-foreground">This usually takes 30-60 seconds</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={handleCancelGeneration}>Cancel</Button>
                </div>
                <div className="bg-muted rounded-xl p-4 mb-6 border border-border">
                  <p className="text-sm text-muted-foreground font-medium mb-1">Your question:</p>
                  <p className="text-foreground">{question}</p>
                </div>
                <GenerationProgress processId={processId} onComplete={handleGenerationComplete} />
              </div>
            ) : (
              <>
                {/* Chat bubble + example pills */}
                <div className="p-6 pb-3">
                  <div className="flex gap-3 mb-5">
                    <div className="w-8 h-8 bg-gradient-to-br from-[var(--canvas-primary)] to-[var(--canvas-secondary)] rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-sm">✨</span>
                    </div>
                    <div className="bg-muted rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%]">
                      <p className="text-muted-foreground text-sm leading-relaxed">
                        I can transform any educational topic into an interactive game. Try one of these:
                      </p>
                    </div>
                  </div>

                  {/* Example questions : always visible, compact */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 pl-11" role="list" aria-label="Example questions">
                    {(selectedPreset === 'v4' && selectedTemplate === 'algorithm_game' ? ALGORITHM_QUESTIONS : DIAGRAM_QUESTIONS).map((example, i) => (
                      <button
                        key={i}
                        onClick={() => setQuestion(example.text)}
                        className="text-left flex items-start gap-1.5 px-3 py-2 rounded-lg text-xs border border-border bg-background hover:bg-muted hover:border-foreground/20 text-muted-foreground hover:text-foreground transition-all"
                        role="listitem"
                      >
                        <span className="flex-shrink-0">{example.icon}</span>
                        <span className="leading-tight">{example.text}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Input area */}
                <div className="chat-input-area p-4">
                  <div className="relative">
                    <textarea
                      ref={textareaRef}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Describe what you want students to learn..."
                      className="chat-input w-full min-h-[60px] max-h-[200px] pr-14 py-3 px-4 rounded-xl border border-input bg-background focus:border-[var(--canvas-primary)] focus:ring-2 focus:ring-[var(--canvas-primary)]/20 transition-all resize-none"
                      rows={1}
                      aria-label="Enter your educational question or topic"
                      data-gramm="false"
                      data-gramm_editor="false"
                      data-enable-grammarly="false"
                    />
                    <button
                      onClick={handleGenerate}
                      disabled={loading || !question.trim()}
                      className="chat-send-button"
                      title="Generate game (Enter)"
                      aria-label="Generate game"
                    >
                      {loading ? (
                        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      )}
                    </button>
                  </div>

                  {/* Compact preset pills + hint */}
                  <div className="flex flex-col items-center gap-2 mt-3">
                    <p className="text-xs text-muted-foreground">
                      Press Enter to generate &middot; Shift+Enter for new line
                    </p>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mr-1">Pipeline:</span>
                      {PIPELINE_PRESETS.map((preset) => (
                        <button
                          key={preset.id}
                          onClick={() => setSelectedPreset(preset.id)}
                          className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-all ${
                            selectedPreset === preset.id
                              ? 'bg-[var(--canvas-primary)] text-white shadow-sm'
                              : 'bg-muted text-muted-foreground hover:text-foreground'
                          }`}
                          aria-pressed={selectedPreset === preset.id}
                        >
                          {preset.name}
                          {preset.recommended && selectedPreset !== preset.id && (
                            <span className="ml-1 text-[9px] opacity-60">*</span>
                          )}
                        </button>
                      ))}
                    </div>
                    {selectedPreset === 'v4' && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mr-1">Template:</span>
                        {([
                          { id: 'interactive_diagram' as const, name: 'Interactive Diagram' },
                          { id: 'algorithm_game' as const, name: 'Algorithm Game' },
                        ]).map((tmpl) => (
                          <button
                            key={tmpl.id}
                            onClick={() => setSelectedTemplate(tmpl.id)}
                            className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-all ${
                              selectedTemplate === tmpl.id
                                ? 'bg-[var(--canvas-secondary)] text-white shadow-sm'
                                : 'bg-muted text-muted-foreground hover:text-foreground'
                            }`}
                            aria-pressed={selectedTemplate === tmpl.id}
                          >
                            {tmpl.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </section>

        {/* ═══════════════ 3. How It Works ═══════════════ */}
        <section className="mb-14">
          <h2 className="text-2xl font-bold text-foreground mb-2 text-center">How It Works</h2>
          <p className="text-muted-foreground text-center mb-8 max-w-xl mx-auto">
            From question to playable game in under 60 seconds.
          </p>

          <div className="flex flex-col lg:flex-row items-center lg:items-stretch gap-6 lg:gap-0 max-w-4xl mx-auto">
            {[
              { step: 1, title: 'Describe', desc: 'Enter your learning objective or topic', icon: '💬', bg: 'bg-blue-50 dark:bg-blue-900/30' },
              { step: 2, title: 'Generate', desc: 'AI agents design mechanics, scenes & assets', icon: '⚡', bg: 'bg-purple-50 dark:bg-purple-900/30' },
              { step: 3, title: 'Learn', desc: 'Students practice with instant feedback', icon: '📚', bg: 'bg-green-50 dark:bg-green-900/30' },
              { step: 4, title: 'Assess', desc: 'Gamified assessments measure understanding', icon: '📝', bg: 'bg-orange-50 dark:bg-orange-900/30' },
            ].map((step, i, arr) => (
              <div key={step.step} className="flex items-center flex-1 min-w-0">
                <div className="feature-card text-center w-full">
                  <div className={`feature-icon ${step.bg} mx-auto`} aria-hidden="true">
                    <span className="text-2xl">{step.icon}</span>
                  </div>
                  <h3 className="font-semibold text-foreground mb-1">{step.step}. {step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.desc}</p>
                </div>
                {i < arr.length - 1 && (
                  <svg width="28" height="28" viewBox="0 0 28 28" className="hidden lg:block flex-shrink-0 text-muted-foreground/30 mx-1" aria-hidden="true">
                    <path d="M10 6l8 8-8 8" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ═══════════════ 4. Game Library (moved up!) ═══════════════ */}
        <section className="mb-14">
          <h2 className="text-2xl font-bold text-foreground mb-2 text-center">Game Library</h2>

          <div className="max-w-6xl mx-auto">
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {([
                { id: 'diagram', label: 'Interactive Diagram', icon: '🎯', count: '9 mechanics' },
                { id: 'algorithm', label: 'Interactive Algorithm', icon: '🧩', count: '6 mechanics' },
                { id: 'engine', label: 'Shared Engine', icon: '⚙️', count: '9 modules' },
                { id: 'pipeline', label: 'Pipeline UI', icon: '📊', count: '20 components' },
              ] as const).map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setLibraryTab(tab.id)}
                  className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    libraryTab === tab.id
                      ? 'bg-gradient-to-r from-[var(--canvas-primary)] to-[var(--canvas-secondary)] text-white shadow-md'
                      : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:border-foreground/20'
                  }`}
                >
                  <span className="mr-1.5">{tab.icon}</span>
                  {tab.label}
                  <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${
                    libraryTab === tab.id ? 'bg-white/20' : 'bg-muted'
                  }`}>{tab.count}</span>
                </button>
              ))}
            </div>

            {/* ── Interactive Diagram Template ── */}
            {libraryTab === 'diagram' && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Interaction Mechanics</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {[
                      { name: 'Drag & Drop', icon: '🎯', desc: 'Drag labels onto zones with leader lines and spring physics', needs: 'Diagram', href: '/demo/drag-drop' },
                      { name: 'Click to Identify', icon: '👆', desc: 'Click zones in response to progressive prompts', needs: 'Diagram', href: '/demo/click-to-identify' },
                      { name: 'Trace Path', icon: '✏️', desc: 'Draw paths through waypoints with particle systems', needs: 'Diagram', href: '/demo/trace-path' },
                      { name: 'Sequencing', icon: '🔢', desc: 'Reorder items into correct sequence with multiple layouts', needs: 'Content', href: '/demo/sequencing' },
                      { name: 'Sorting Categories', icon: '📂', desc: 'Drag items into buckets, supports Venn diagrams', needs: 'Content', href: '/demo/sorting-categories' },
                      { name: 'Memory Match', icon: '🃏', desc: '3D card flip with 5 game variants', needs: 'Content', href: '/demo/memory-match' },
                      { name: 'Branching Scenario', icon: '🌳', desc: 'Decision trees with consequences and narrative flow', needs: 'Content', href: '/demo/branching-scenario' },
                      { name: 'Compare & Contrast', icon: '⚖️', desc: 'Side-by-side dual diagrams with categorization', needs: 'Dual', href: '/demo/compare-contrast' },
                      { name: 'Description Matching', icon: '🔗', desc: 'Match text descriptions to diagram zones', needs: 'Diagram', href: '/demo/description-matching' },
                    ].map((m) => (
                      <Link key={m.name} href={m.href} className="block bg-card border border-border rounded-lg p-3 hover:shadow-md transition-shadow hover:border-foreground/20">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">{m.icon}</span>
                          <span className="font-semibold text-foreground text-sm">{m.name}</span>
                          <span className={`text-[9px] ml-auto px-1.5 py-0.5 rounded-full font-medium ${
                            m.needs === 'Diagram' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                            : m.needs === 'Dual' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                            : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          }`}>{m.needs}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{m.desc}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-muted text-muted-foreground">1 demo</span>
                          <span className="text-[10px] text-muted-foreground">Play &rarr;</span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Core Components</p>
                    <ul className="space-y-1.5 text-sm text-foreground">
                      {['DiagramCanvas', 'DraggableLabel', 'DropZone', 'ZoomPanCanvas', 'LeaderLineOverlay', 'MechanicRouter', 'GameControls', 'ResultsPanel', 'SceneTransition'].map((c) => (
                        <li key={c} className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /><code className="text-xs font-mono">{c}</code></li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Hooks</p>
                    <ul className="space-y-1.5 text-sm text-foreground">
                      {['useInteractiveDiagramState', 'useMechanicDispatch', 'useCommandHistory', 'useEventLog', 'usePersistence', 'useZoneCollision', 'useReducedMotion'].map((h) => (
                        <li key={h} className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-purple-500" /><code className="text-xs font-mono">{h}</code></li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Subsystems</p>
                    <ul className="space-y-1.5 text-sm text-foreground">
                      {[
                        { name: 'Commands', desc: 'Undo/redo via command pattern' },
                        { name: 'Events', desc: 'Game event logging' },
                        { name: 'Animations', desc: 'Confetti, transitions' },
                        { name: 'Accessibility', desc: 'Keyboard nav, screen reader' },
                        { name: 'Persistence', desc: 'Save/load game state' },
                        { name: 'Schemas', desc: 'Blueprint parsing + Zod' },
                      ].map((s) => (
                        <li key={s.name} className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /><span className="text-xs"><code className="font-mono">{s.name}</code> <span className="text-muted-foreground">&mdash; {s.desc}</span></span></li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* ── Algorithm Games Template ── */}
            {libraryTab === 'algorithm' && (
              <div className="space-y-6 animate-fade-in">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    { name: 'State Tracer', icon: '🔍', desc: 'Step through execution, predict variable states', demos: 8, href: '/demo/state-tracer', color: 'from-blue-500/20 to-blue-600/10', border: 'border-blue-500/30 hover:border-blue-400', hook: 'useStateTracerMachine', components: ['PredictionPanel', 'ArrangementPrediction', '7 Visualizers'] },
                    { name: 'Bug Hunter', icon: '🐛', desc: 'Find and fix bugs through interactive debugging', demos: 8, href: '/demo/bug-hunter', color: 'from-red-500/20 to-red-600/10', border: 'border-red-500/30 hover:border-red-400', hook: 'useBugHunterMachine', components: ['ClickableCodePanel', 'CodeFixEditor', 'FixPanel', 'TestCasePanel'] },
                    { name: 'Algorithm Builder', icon: '🧩', desc: 'Parsons problems: arrange blocks into correct order', demos: 8, href: '/demo/algorithm-builder', color: 'from-green-500/20 to-green-600/10', border: 'border-green-500/30 hover:border-green-400', hook: 'useAlgorithmBuilderMachine', components: ['SourcePanel', 'SolutionPanel', 'SortableCodeBlock', 'IndentControls'] },
                    { name: 'Complexity Analyzer', icon: '📊', desc: 'Determine Big-O from code and growth data', demos: 8, href: '/demo/complexity-analyzer', color: 'from-purple-500/20 to-purple-600/10', border: 'border-purple-500/30 hover:border-purple-400', hook: 'useComplexityAnalyzerMachine', components: ['ComplexityCodePanel', 'GrowthDataPanel', 'ComplexityOptionGrid'] },
                    { name: 'Constraint Puzzle', icon: '🧮', desc: '6 board types, declarative constraints, generic scoring', demos: 7, href: '/demo/constraint-puzzle', color: 'from-yellow-500/20 to-yellow-600/10', border: 'border-yellow-500/30 hover:border-yellow-400', hook: 'useGenericConstraintPuzzleMachine', components: ['BoardRouter', '6 Board Types', 'ConstraintFeedbackBar'] },
                    { name: 'Combined Puzzle', icon: '🔬', desc: 'Code challenge + manual puzzle with solution comparison', demos: 4, href: '/demo/combined-puzzle', color: 'from-cyan-500/20 to-cyan-600/10', border: 'border-cyan-500/30 hover:border-cyan-400', hook: 'useCombinedPuzzleMachine', components: ['AlgorithmCodePanel', 'CodeEditorPanel', 'TestRunnerPanel', 'PyodideService'] },
                  ].map((game) => (
                    <Link key={game.name} href={game.href} className={`block text-left p-4 rounded-xl border-2 transition-all bg-gradient-to-br ${game.color} ${game.border} hover:shadow-md`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-2xl">{game.icon}</span>
                        <h3 className="font-bold text-foreground">{game.name}</h3>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">{game.desc}</p>
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                          <code className="text-[10px] font-mono text-muted-foreground">{game.hook}</code>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {game.components.map((c) => (
                            <span key={c} className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">{c}</span>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-3">
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-muted text-muted-foreground">{game.demos} demos</span>
                        <span className="text-[10px] text-muted-foreground">Play &rarr;</span>
                      </div>
                    </Link>
                  ))}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Shared Components</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['HintSystem', 'ScoreDisplay', 'CompletionScreen', 'FeedbackToast', 'DiffOverlay', 'VerificationPanel', 'RoundHeader', 'BugCounter'].map((c) => (
                        <span key={c} className="text-[10px] px-2 py-1 rounded-md bg-muted text-muted-foreground font-mono border border-border">{c}</span>
                      ))}
                    </div>
                  </div>
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Data Visualizers</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['ArrayVisualizer', 'GraphVisualizer', 'TreeVisualizer', 'DPTableVisualizer', 'StackVisualizer', 'LinkedListVisualizer'].map((v) => (
                        <span key={v} className="text-[10px] px-2 py-1 rounded-md bg-violet-100 text-violet-700 dark:bg-violet-900/20 dark:text-violet-400 font-mono border border-violet-200 dark:border-violet-800">{v}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── Shared Engine Layer ── */}
            {libraryTab === 'engine' && (
              <div className="space-y-4 animate-fade-in">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    { name: 'Scoring Engine', file: 'scoringEngine.ts', desc: 'Configurable scoring with streaks, penalties, and bonuses.', icon: '🏆', color: 'border-yellow-400 bg-yellow-50/50 dark:bg-yellow-900/10' },
                    { name: 'Feedback Engine', file: 'feedbackEngine.ts', desc: 'Context-aware feedback for correctness, hints, and motivation.', icon: '💬', color: 'border-green-400 bg-green-50/50 dark:bg-green-900/10' },
                    { name: 'Completion Detector', file: 'completionDetector.ts', desc: 'Detect completion across mechanic types and scenes.', icon: '✅', color: 'border-blue-400 bg-blue-50/50 dark:bg-blue-900/10' },
                    { name: 'Scene Flow Graph', file: 'sceneFlowGraph.ts', desc: 'DAG of scenes with entry conditions and transitions.', icon: '🔀', color: 'border-purple-400 bg-purple-50/50 dark:bg-purple-900/10' },
                    { name: 'Transition Evaluator', file: 'transitionEvaluator.ts', desc: 'Mode transitions, multi-mechanic sequencing, mutex.', icon: '🔄', color: 'border-indigo-400 bg-indigo-50/50 dark:bg-indigo-900/10' },
                    { name: 'Mechanic Registry', file: 'mechanicRegistry.ts', desc: 'O(1) dispatch to renderers, initializers, validators.', icon: '📋', color: 'border-orange-400 bg-orange-50/50 dark:bg-orange-900/10' },
                    { name: 'Rule Schema', file: 'ruleSchema.ts', desc: 'Declarative constraints, acceptance criteria, multipliers.', icon: '📐', color: 'border-pink-400 bg-pink-50/50 dark:bg-pink-900/10' },
                    { name: 'Blueprint Parser', file: 'parseBlueprint.ts', desc: 'Parse and normalize backend blueprints with Zod.', icon: '📝', color: 'border-cyan-400 bg-cyan-50/50 dark:bg-cyan-900/10' },
                    { name: 'Correctness Evaluator', file: 'correctnessEvaluator.ts', desc: 'Partial credit, fuzzy matching, tolerance.', icon: '🎯', color: 'border-red-400 bg-red-50/50 dark:bg-red-900/10' },
                  ].map((mod) => (
                    <div key={mod.name} className={`rounded-xl border-2 ${mod.color} p-4 transition-shadow hover:shadow-md`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">{mod.icon}</span>
                        <h3 className="font-semibold text-foreground text-sm">{mod.name}</h3>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{mod.desc}</p>
                      <code className="text-[10px] text-muted-foreground font-mono">{mod.file}</code>
                    </div>
                  ))}
                </div>
                <div className="bg-card border border-border rounded-xl p-4">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Constraint Puzzle Board Types (Generic, Data-Driven)</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                    {[
                      { name: 'Item Selection', icon: '✅', example: 'Knapsack' },
                      { name: 'Grid Placement', icon: '🔲', example: 'N-Queens' },
                      { name: 'Multiset Building', icon: '🪙', example: 'Coin Change' },
                      { name: 'Graph Interaction', icon: '🌐', example: 'MST' },
                      { name: 'Value Assignment', icon: '🎨', example: 'Graph Coloring' },
                      { name: 'Sequence Building', icon: '📚', example: 'Topological Sort' },
                    ].map((b) => (
                      <div key={b.name} className="text-center p-3 rounded-lg bg-muted/50 border border-border">
                        <div className="text-xl mb-1">{b.icon}</div>
                        <div className="text-xs font-medium text-foreground">{b.name}</div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">{b.example}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── Pipeline Observability UI ── */}
            {libraryTab === 'pipeline' && (
              <div className="space-y-4 animate-fade-in">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Visualization</p>
                    <ul className="space-y-1.5">
                      {[
                        { name: 'PipelineView', desc: 'Main DAG visualization with 59+ agent metadata' },
                        { name: 'LivePipelineView', desc: 'Real-time SSE-powered pipeline view' },
                        { name: 'TimelineView', desc: 'Horizontal timeline of stage execution' },
                        { name: 'ClusterView', desc: 'HAD cluster visualization' },
                        { name: 'ZoneOverlay', desc: 'Zone bounding-box overlay on images' },
                        { name: 'AgentNode', desc: 'Individual agent node in DAG' },
                      ].map((c) => (
                        <li key={c.name} className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" /><span className="text-xs"><code className="font-mono font-medium text-foreground">{c.name}</code> <span className="text-muted-foreground">&mdash; {c.desc}</span></span></li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Analytics</p>
                    <ul className="space-y-1.5">
                      {[
                        { name: 'TokenChart', desc: 'Token usage per agent bar chart' },
                        { name: 'LiveTokenCounter', desc: 'Real-time token accumulator' },
                        { name: 'CostBreakdown', desc: 'Cost per model, per stage' },
                        { name: 'ReActTraceViewer', desc: 'Step-by-step ReAct reasoning trace' },
                        { name: 'ToolCallHistory', desc: 'Tool invocation timeline' },
                        { name: 'LiveReasoningPanel', desc: 'Streaming agent reasoning' },
                      ].map((c) => (
                        <li key={c.name} className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1.5 shrink-0" /><span className="text-xs"><code className="font-mono font-medium text-foreground">{c.name}</code> <span className="text-muted-foreground">&mdash; {c.desc}</span></span></li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Detail Panels</p>
                    <ul className="space-y-1.5">
                      {[
                        { name: 'StagePanel', desc: 'Detailed stage I/O with JSON viewer' },
                        { name: 'StageDetailSection', desc: 'Collapsible stage detail sections' },
                        { name: 'SubTaskPanel', desc: 'Parallel sub-task visualization' },
                        { name: 'RetryHistory', desc: 'Retry attempts with diffs' },
                        { name: 'RetryBreadcrumb', desc: 'Navigation across retry attempts' },
                        { name: 'RunHistoryCard', desc: 'Historical run summary cards' },
                      ].map((c) => (
                        <li key={c.name} className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 shrink-0" /><span className="text-xs"><code className="font-mono font-medium text-foreground">{c.name}</code> <span className="text-muted-foreground">&mdash; {c.desc}</span></span></li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-card border border-border rounded-xl p-4">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">UI Kit (Shared)</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['Button', 'Card', 'Dialog', 'Select', 'DropdownMenu', 'Input', 'Badge', 'Skeleton', 'VirtualizedList', 'ThemeToggle'].map((c) => (
                        <span key={c} className="text-[10px] px-2 py-1 rounded-md bg-muted text-muted-foreground font-mono border border-border">{c}</span>
                      ))}
                    </div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mt-4 mb-2">Enhanced Components</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['MathGraph', 'SimpleChart', 'InteractiveMap', 'MoleculeViewer', 'PhysicsSimulation'].map((c) => (
                        <span key={c} className="text-[10px] px-2 py-1 rounded-md bg-indigo-100 text-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-400 font-mono border border-indigo-200 dark:border-indigo-800">{c}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ═══════════════ 5. Under the Hood (consolidated tech sections) ═══════════════ */}
        <section className="mb-14">
          <h2 className="text-2xl font-bold text-foreground mb-2 text-center">Under the Hood</h2>
          <p className="text-muted-foreground text-center mb-8 max-w-2xl mx-auto">
            Explore the multi-agent pipeline architecture powering game generation.
          </p>

          {/* Tech tabs */}
          <div className="flex flex-wrap justify-center gap-2 mb-8">
            {([
              { id: 'architecture', label: 'Architecture' },
              { id: 'pipeline', label: 'Pipeline Stages' },
              { id: 'dataflow', label: 'Data Flow' },
              { id: 'research', label: 'Research' },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setTechTab(tab.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  techTab === tab.id
                    ? 'bg-foreground text-background shadow-sm'
                    : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:border-foreground/20'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── Architecture Tab ── */}
          {techTab === 'architecture' && (
            <div className="animate-fade-in">
              <div className="flex justify-center gap-2 mb-6">
                {PIPELINE_PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => setSelectedPreset(preset.id)}
                    className={`text-xs px-3 py-1.5 rounded-full font-medium transition-all ${
                      selectedPreset === preset.id
                        ? 'bg-[var(--canvas-primary)] text-white'
                        : 'bg-muted text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {preset.name}
                  </button>
                ))}
              </div>

              <p className="text-muted-foreground text-center mb-8 text-sm max-w-2xl mx-auto">
                {selectedPreset === 'preset_1'
                  ? '17 specialized agents in a linear pipeline. Each agent runs once, passing state to the next.'
                  : selectedPreset === 'v3'
                    ? '5-phase ReAct pipeline where each phase uses a reasoning loop with tool calls before handing off.'
                    : '3-stage creative cascade with parallel Send API dispatch, contract validation, and retry loops.'}
              </p>

              <div className="max-w-5xl mx-auto">
                {/* ── V4: Full React Flow DAG ── */}
                {selectedPreset === 'v4' && (
                  <div className="animate-fade-in">
                    <V4PipelineDAG />
                    <div className="text-center text-xs text-muted-foreground mt-3">
                      17 node types · 5 merge nodes · 4 Send API fan-outs · 3 retry loops · 2 contract validators
                    </div>
                  </div>
                )}

                {/* ── Sequential / V3: Horizontal phase chips + expand ── */}
                {selectedPreset !== 'v4' && (() => {
                  const presetPhases = selectedPreset === 'preset_1' ? [
                    { id: 'seq_ctx', label: 'Context', count: 3, borderCls: 'border-blue-400', bgCls: 'bg-blue-50/50 dark:bg-blue-900/10', textCls: 'text-blue-700 dark:text-blue-400', agents: [
                      { name: 'Input Enhancer', type: 'llm', desc: 'Enrich question with pedagogy context' },
                      { name: 'DK Retriever', type: 'llm', desc: 'Retrieve curriculum standards, concepts' },
                      { name: 'Router', type: 'deterministic', desc: 'Select pipeline preset' },
                    ]},
                    { id: 'seq_design', label: 'Design', count: 4, borderCls: 'border-purple-400', bgCls: 'bg-purple-50/50 dark:bg-purple-900/10', textCls: 'text-purple-700 dark:text-purple-400', agents: [
                      { name: 'Game Designer', type: 'llm', desc: 'Design mechanics, scenes, objectives' },
                      { name: 'Design Validator', type: 'deterministic', desc: 'Schema + pedagogical validation' },
                      { name: 'Scene Architect', type: 'llm', desc: 'Spatial layout of zones and labels' },
                      { name: 'Scene Validator', type: 'deterministic', desc: 'Validate scene specs' },
                    ]},
                    { id: 'seq_interact', label: 'Interactions', count: 2, borderCls: 'border-pink-400', bgCls: 'bg-pink-50/50 dark:bg-pink-900/10', textCls: 'text-pink-700 dark:text-pink-400', agents: [
                      { name: 'Interaction Designer', type: 'llm', desc: 'Mechanic content: paths, sequences, pairs' },
                      { name: 'Interaction Validator', type: 'deterministic', desc: 'Validate against mechanic schemas' },
                    ]},
                    { id: 'seq_asset', label: 'Assets', count: 4, borderCls: 'border-orange-400', bgCls: 'bg-orange-50/50 dark:bg-orange-900/10', textCls: 'text-orange-700 dark:text-orange-400', agents: [
                      { name: 'Asset Spec Builder', type: 'llm', desc: 'Image generation prompts per scene' },
                      { name: 'Image Generator', type: 'llm', desc: 'Generate diagram images via AI' },
                      { name: 'Zone Detector', type: 'llm', desc: 'Gemini Flash bounding-box detection' },
                      { name: 'Label Mapper', type: 'deterministic', desc: 'Map detected zones to game labels' },
                    ]},
                    { id: 'seq_output', label: 'Output', count: 4, borderCls: 'border-green-400', bgCls: 'bg-green-50/50 dark:bg-green-900/10', textCls: 'text-green-700 dark:text-green-400', agents: [
                      { name: 'Blueprint Assembler', type: 'deterministic', desc: 'Assemble into playable blueprint' },
                      { name: 'Blueprint Validator', type: 'deterministic', desc: 'Final schema + completeness check' },
                      { name: 'Scoring Engine', type: 'deterministic', desc: 'Configure scoring rules per mechanic' },
                      { name: 'Output Formatter', type: 'deterministic', desc: 'Emit final JSON for frontend' },
                    ]},
                  ] : [
                    { id: 'v3_ctx', label: 'Context', count: 3, borderCls: 'border-blue-400', bgCls: 'bg-blue-50/50 dark:bg-blue-900/10', textCls: 'text-blue-700 dark:text-blue-400', agents: [
                      { name: 'Input Enhancer', type: 'llm', desc: 'Enrich question with pedagogy' },
                      { name: 'DK Retriever', type: 'llm', desc: 'Curriculum + canonical labels' },
                      { name: 'Router', type: 'deterministic', desc: 'Select pipeline preset' },
                    ]},
                    { id: 'v3_design', label: 'Game Design', count: 2, borderCls: 'border-purple-400', bgCls: 'bg-purple-50/50 dark:bg-purple-900/10', textCls: 'text-purple-700 dark:text-purple-400', badges: ['ReAct', 'retry'], agents: [
                      { name: 'Game Designer V3', type: 'react', desc: 'ReAct loop with 5 tools: analyze, plan, design, validate, submit' },
                      { name: 'Design Validator', type: 'deterministic', desc: 'Schema validation + retry gate' },
                    ]},
                    { id: 'v3_scene', label: 'Scenes', count: 2, borderCls: 'border-indigo-400', bgCls: 'bg-indigo-50/50 dark:bg-indigo-900/10', textCls: 'text-indigo-700 dark:text-indigo-400', badges: ['ReAct', 'retry'], agents: [
                      { name: 'Scene Architect V3', type: 'react', desc: 'ReAct loop with 5 tools: spatial layout, zone planning, mechanic content' },
                      { name: 'Scene Validator', type: 'deterministic', desc: 'Schema validation + retry gate' },
                    ]},
                    { id: 'v3_interact', label: 'Interactions', count: 2, borderCls: 'border-pink-400', bgCls: 'bg-pink-50/50 dark:bg-pink-900/10', textCls: 'text-pink-700 dark:text-pink-400', badges: ['ReAct', 'retry'], agents: [
                      { name: 'Interaction Designer V3', type: 'react', desc: 'ReAct loop with 5 tools: scoring, feedback, paths, sequences' },
                      { name: 'Interaction Validator', type: 'deterministic', desc: 'Schema validation + retry gate' },
                    ]},
                    { id: 'v3_asset', label: 'Assets', count: 1, borderCls: 'border-orange-400', bgCls: 'bg-orange-50/50 dark:bg-orange-900/10', textCls: 'text-orange-700 dark:text-orange-400', badges: ['ReAct'], agents: [
                      { name: 'Asset Generator V3', type: 'react', desc: 'ReAct loop with 5 tools: image gen, zone detection, SAM3 segmentation' },
                    ]},
                    { id: 'v3_assemble', label: 'Assembly', count: 1, borderCls: 'border-green-400', bgCls: 'bg-green-50/50 dark:bg-green-900/10', textCls: 'text-green-700 dark:text-green-400', agents: [
                      { name: 'Blueprint Assembler V3', type: 'react', desc: 'ReAct loop with 4 tools: assemble, validate, repair, finalize' },
                    ]},
                  ]

                  const selected = presetPhases.find(p => p.id === expandedCluster)

                  return (
                    <div>
                      <div className="flex items-center justify-center gap-1 flex-wrap">
                        {presetPhases.map((phase, i) => (
                          <div key={phase.id} className="flex items-center">
                            <button
                              onClick={() => setExpandedCluster(expandedCluster === phase.id ? null : phase.id)}
                              className={`relative rounded-lg border-2 px-3 py-2 transition-all text-center min-w-[90px] ${phase.borderCls} ${phase.bgCls} ${
                                expandedCluster === phase.id ? 'ring-2 ring-offset-1 ring-[var(--canvas-primary)]/40 shadow-md scale-105' : 'hover:shadow-sm hover:scale-[1.02]'
                              }`}
                            >
                              <p className={`text-[10px] font-bold uppercase tracking-wider ${phase.textCls}`}>{phase.label}</p>
                              <p className="text-[10px] text-muted-foreground mt-0.5">{phase.count} {phase.count === 1 ? 'node' : 'nodes'}</p>
                              {(phase as { badges?: string[] }).badges && (
                                <div className="flex flex-wrap gap-0.5 mt-1 justify-center">
                                  {((phase as { badges?: string[] }).badges ?? []).map((b: string) => (
                                    <span key={b} className="text-[8px] px-1 py-px rounded bg-muted text-muted-foreground">{b}</span>
                                  ))}
                                </div>
                              )}
                            </button>
                            {i < presetPhases.length - 1 && (
                              <svg width="20" height="12" viewBox="0 0 20 12" className="text-muted-foreground shrink-0 mx-0.5"><line x1="0" y1="6" x2="13" y2="6" stroke="currentColor" strokeWidth="1.5" /><polygon points="13,2 20,6 13,10" fill="currentColor" /></svg>
                            )}
                          </div>
                        ))}
                      </div>

                      {selected && (
                        <div className={`mt-4 rounded-xl border-2 ${selected.borderCls} ${selected.bgCls} p-4 animate-fade-in`}>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className={`font-semibold text-sm uppercase tracking-wider ${selected.textCls}`}>{selected.label}</h3>
                            <button onClick={() => setExpandedCluster(null)} className="text-xs text-muted-foreground hover:text-foreground">&times; close</button>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {selected.agents.map((agent) => (
                              <div key={agent.name} className="flex items-start gap-2 rounded-lg border border-border bg-white/60 dark:bg-white/5 px-3 py-2">
                                <span className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0 ${
                                  agent.type === 'react' ? 'bg-violet-500'
                                  : agent.type === 'llm' ? 'bg-violet-500'
                                  : 'bg-slate-500'
                                }`}>
                                  {agent.type === 'react' ? 'R' : agent.type === 'llm' ? 'AI' : 'D'}
                                </span>
                                <div className="min-w-0">
                                  <p className="text-sm font-medium text-foreground leading-tight">{agent.name}</p>
                                  <p className="text-xs text-muted-foreground">{agent.desc}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="flex gap-3 mt-3 pt-2 border-t border-border justify-center flex-wrap">
                            <span className="flex items-center gap-1 text-[10px] text-muted-foreground"><span className="w-3 h-3 rounded-full bg-violet-500" /> LLM / ReAct</span>
                            <span className="flex items-center gap-1 text-[10px] text-muted-foreground"><span className="w-3 h-3 rounded-full bg-slate-500" /> Deterministic</span>
                          </div>
                        </div>
                      )}

                      <div className="text-center text-xs text-muted-foreground mt-3">
                        {selectedPreset === 'preset_1' && '17 agents · linear execution · validator after each LLM stage'}
                        {selectedPreset === 'v3' && '12 agents · 22 tools · 5 validation gates with retry loops'}
                      </div>
                    </div>
                  )
                })()}
              </div>
            </div>
          )}

          {/* ── Pipeline Stages Tab ── */}
          {techTab === 'pipeline' && (
            <div className="animate-fade-in">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-4xl mx-auto">
                {[
                  { phase: 1, title: 'Domain Knowledge & Pedagogy', desc: 'Retrieves curriculum-aligned content, Bloom\'s taxonomy mapping, misconception databases', color: 'border-blue-500' },
                  { phase: 2, title: 'Game Design', desc: 'Selects mechanics, designs scoring rubrics, creates pedagogical feedback loops', color: 'border-purple-500' },
                  { phase: 3, title: 'Scene Architecture', desc: 'Structures visual scenes, maps learning objectives to spatial zones', color: 'border-indigo-500' },
                  { phase: 4, title: 'Interaction Design', desc: 'Enriches mechanic-specific content including sequences, paths, branching trees, matching pairs', color: 'border-teal-500' },
                  { phase: 5, title: 'Asset Generation', desc: 'AI diagram generation + Gemini zone detection + SAM3 segmentation', color: 'border-orange-500' },
                  { phase: 6, title: 'Blueprint Assembly', desc: 'Validates, repairs, and assembles final playable blueprint with all configs', color: 'border-green-500' },
                ].map((stage) => (
                  <div key={stage.phase} className={`relative bg-card rounded-xl p-5 border border-border border-l-4 ${stage.color} shadow-sm hover:shadow-md transition-shadow`}>
                    <div className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-bold text-foreground">{stage.phase}</span>
                      <div>
                        <h3 className="font-semibold text-foreground mb-1">{stage.title}</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">{stage.desc}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Data Flow Tab ── */}
          {techTab === 'dataflow' && (
            <div className="animate-fade-in">
              <div className="flex flex-wrap items-center justify-center gap-y-3 gap-x-1 max-w-5xl mx-auto">
                {([
                  { id: 'input', label: 'Teacher Input', highlight: true },
                  { id: 'domain', label: 'Domain Knowledge', highlight: false },
                  { id: 'design', label: 'Game Design', highlight: false },
                  { id: 'scenes', label: 'Scene Layout', highlight: false },
                  { id: 'interactions', label: 'Interactions', highlight: false },
                  { id: 'assets', label: 'Assets', highlight: false },
                  { id: 'blueprint', label: 'Blueprint', highlight: false },
                  { id: 'game', label: 'Playable Game', highlight: true },
                ] as const).map((step, i, arr) => (
                  <div key={step.id} className="flex items-center">
                    <button
                      onClick={() => setExpandedStage(expandedStage === step.id ? null : step.id)}
                      className={`px-4 py-2.5 rounded-full text-sm font-medium whitespace-nowrap border transition-all ${expandedStage === step.id ? 'ring-2 ring-[var(--canvas-primary)]/40 shadow-md' : 'hover:shadow-sm'} ${step.highlight ? 'bg-gradient-to-r from-[var(--canvas-primary)] to-[var(--canvas-secondary)] text-white border-transparent shadow-md' : 'bg-card text-foreground border-border'}`}
                    >
                      {step.label}
                    </button>
                    {i < arr.length - 1 && (
                      <svg width="24" height="16" viewBox="0 0 24 16" className="flex-shrink-0 text-muted-foreground mx-0.5"><line x1="0" y1="8" x2="16" y2="8" stroke="currentColor" strokeWidth="1.5" /><polygon points="16,4 24,8 16,12" fill="currentColor" /></svg>
                    )}
                  </div>
                ))}
              </div>

              {expandedStage && (() => {
                const stages = [
                  { id: 'input', label: 'Teacher Input', scopedIn: ['question_text', 'grade_level', 'subject_area'], scopedOut: ['parsed_question', 'bloom_level', 'topic_keywords'], graphWrites: 'GameNode (root)', note: 'Entry point that creates the root game node in the graph store.' },
                  { id: 'domain', label: 'Domain Knowledge', scopedIn: ['parsed_question', 'bloom_level', 'topic_keywords'], scopedOut: ['domain_knowledge', 'misconceptions[]', 'curriculum_standards[]'], graphWrites: 'ConceptNodes, MisconceptionNodes', note: 'Scoped context: only question + topic fields. Writes concept nodes linked to root.' },
                  { id: 'design', label: 'Game Design', scopedIn: ['domain_knowledge', 'bloom_level', 'mechanic_contracts'], scopedOut: ['per_scene: { mechanic_type, scoring_rubric, feedback_rules }'], graphWrites: 'SceneNodes, MechanicNodes (per scene)', note: 'Per-scene mechanics selected from contract registry. Each scene gets its own subgraph.' },
                  { id: 'scenes', label: 'Scene Layout', scopedIn: ['per_scene: { mechanic_type, domain_knowledge_slice }'], scopedOut: ['per_scene: { zone_layout, spatial_mapping, objective_map }'], graphWrites: 'ZoneNodes, SpatialEdges (per scene)', note: 'Parallel execution per scene. Each scene receives only its scoped domain knowledge slice.' },
                  { id: 'interactions', label: 'Interactions', scopedIn: ['per_scene_per_mechanic: { mechanic_type, zones, domain_slice }'], scopedOut: ['per_mechanic: { sequences, paths, pairs, branches, match_rules }'], graphWrites: 'InteractionNodes, RuleNodes (per mechanic)', note: 'Per-scene, per-mechanic enrichment. Writes FOL rules: scoring predicates, feedback triggers.' },
                  { id: 'assets', label: 'Assets', scopedIn: ['per_scene: { asset_needs, zone_layout }'], scopedOut: ['per_asset: { image_url, zone_masks[], bounding_boxes[] }'], graphWrites: 'ImageNodes, AssetEdges (per asset type)', note: 'Per-scene, per-asset-type parallel generation. Graph links: Image -> Zone -> Label.' },
                  { id: 'blueprint', label: 'Blueprint', scopedIn: ['full_game_graph (all stage subgraphs merged)'], scopedOut: ['playable_blueprint JSON'], graphWrites: 'Final GameGraph serialization', note: 'Merges all stage graphs via topological sort. Validates schema contracts. Emits blueprint.' },
                  { id: 'game', label: 'Playable Game', scopedIn: ['playable_blueprint'], scopedOut: ['Rendered interactive game with scoring, feedback, transitions'], graphWrites: 'Frontend hydrates blueprint -> Zustand store', note: 'Frontend mechanic registry routes each scene to its component. Rules engine evaluates FOL.' },
                ]
                const stage = stages.find(s => s.id === expandedStage)
                if (!stage) return null
                return (
                  <div className="mt-6 max-w-3xl mx-auto bg-card border border-border rounded-xl p-5 shadow-sm animate-fade-in">
                    <h3 className="font-semibold text-foreground mb-3">{stage.label}</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-3">
                      <div>
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5">Scoped Context In</p>
                        <div className="space-y-1">
                          {stage.scopedIn.map((field) => (
                            <div key={field} className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /><code className="text-xs text-foreground bg-muted px-1.5 py-0.5 rounded font-mono">{field}</code></div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5">Stage Output</p>
                        <div className="space-y-1">
                          {stage.scopedOut.map((field) => (
                            <div key={field} className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-green-500" /><code className="text-xs text-foreground bg-muted px-1.5 py-0.5 rounded font-mono">{field}</code></div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="pt-3 border-t border-border">
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1">Graph Store Writes</p>
                      <code className="text-xs text-[var(--canvas-primary)] font-mono">{stage.graphWrites}</code>
                      <p className="text-xs text-muted-foreground mt-2 leading-relaxed">{stage.note}</p>
                    </div>
                  </div>
                )
              })()}
            </div>
          )}

          {/* ── Research Tab ── */}
          {techTab === 'research' && (
            <div className="animate-fade-in">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-4xl mx-auto">
                {[
                  { icon: '🤖', title: 'Agentic AI Architectures', desc: '11 frameworks evaluated including LangGraph, CrewAI, AutoGen, DSPy, and more', bg: 'bg-blue-50 dark:bg-blue-900/20' },
                  { icon: '🔄', title: 'ReAct Reasoning', desc: 'Multi-step tool-calling loops with observation-action cycles', bg: 'bg-purple-50 dark:bg-purple-900/20' },
                  { icon: '🎮', title: 'Gamification in Education', desc: 'Bloom\'s taxonomy alignment, misconception-driven feedback', bg: 'bg-green-50 dark:bg-green-900/20' },
                  { icon: '👁️', title: 'Computer Vision Pipeline', desc: 'Gemini Flash bounding boxes + SAM3 pixel-perfect segmentation', bg: 'bg-orange-50 dark:bg-orange-900/20' },
                  { icon: '✅', title: 'Quality Assurance', desc: 'Validator agents with retry loops, schema-driven contracts', bg: 'bg-teal-50 dark:bg-teal-900/20' },
                  { icon: '🖼️', title: 'Multi-Modal Generation', desc: 'Text-to-diagram, zone detection, asset orchestration', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
                ].map((area) => (
                  <div key={area.title} className={`${area.bg} rounded-xl p-5 border border-border shadow-sm hover:shadow-md transition-shadow`}>
                    <span className="text-2xl mb-3 block" aria-hidden="true">{area.icon}</span>
                    <h3 className="font-semibold text-foreground mb-1">{area.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{area.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ═══════════════ 6. Bottom CTA ═══════════════ */}
        <section className="text-center pb-12">
          <div className="bg-gradient-to-r from-[var(--canvas-primary)]/5 to-[var(--canvas-secondary)]/5 rounded-2xl border border-border p-10 max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-foreground mb-3">Ready to Create?</h2>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Enter any educational topic above and watch the AI pipeline generate your game in real time.
            </p>
            <button
              onClick={() => {
                window.scrollTo({ top: 0, behavior: 'smooth' })
                setTimeout(() => textareaRef.current?.focus(), 500)
              }}
              className="px-6 py-3 bg-gradient-to-r from-[var(--canvas-primary)] to-[var(--canvas-secondary)] text-white font-semibold rounded-xl hover:shadow-lg transition-all"
            >
              Start Creating
            </button>
          </div>
        </section>

      </div>
    </div>
  )
}

'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import React, { useMemo, useState } from 'react';
import { ACL_GAMES, computeAggregateMetrics } from '@/data/acl-demo';
import { DOMAIN_LABELS, DOMAIN_ICONS, DOMAIN_COLORS, MECHANIC_LABELS } from '@/data/acl-demo/types';
import type { Domain } from '@/data/acl-demo/types';
import V4PipelineDAG from '@/components/V4PipelineDAG';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

type Tab = 'home' | 'tryit' | 'video' | 'setup' | 'architecture';

const TABS: { key: Tab; label: string }[] = [
  { key: 'home', label: 'Home' },
  { key: 'tryit', label: 'Try It' },
  { key: 'video', label: 'Video' },
  { key: 'setup', label: 'Getting Started' },
  { key: 'architecture', label: 'Architecture' },
];

const EXAMPLE_QUESTIONS = [
  { text: 'Label the parts of a plant cell and identify their functions', icon: '\u{1F9EC}' },
  { text: 'Trace blood flow through the heart', icon: '\u{2764}\u{FE0F}' },
  { text: 'Sort organisms by trophic level', icon: '\u{1F33F}' },
  { text: 'Order events of the American Revolution', icon: '\u{1F4DC}' },
  { text: 'Compare TCP vs UDP protocols', icon: '\u{1F4BB}' },
  { text: 'Find the bug in this binary search', icon: '\u{1F41B}' },
];

export default function ACLDemoLandingPage() {
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const metrics = useMemo(() => computeAggregateMetrics(ACL_GAMES), []);
  const domainCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    ACL_GAMES.forEach(g => { counts[g.domain] = (counts[g.domain] || 0) + 1; });
    return counts;
  }, []);
  const mechanicCount = useMemo(() => new Set(ACL_GAMES.map(g => g.mechanic)).size, []);
  const [pipelineTab, setPipelineTab] = useState<'diagram' | 'algorithm'>('diagram');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      {/* ═══════════ Nav ═══════════ */}
      <nav className="border-b border-gray-200/60 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Top row: logo + external links */}
          <div className="h-14 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
                GamED.AI
              </span>
              <span className="text-xs font-medium px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full">
                EDUCATIONAL GAMES
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/acl-demo/library" className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors">
                Game Library
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                Code
              </a>
              <a
                href="https://arxiv.org"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
              >
                Paper
              </a>
              <ThemeToggle />
            </div>
          </div>
          {/* Tab bar */}
          <div className="flex gap-1 -mb-px overflow-x-auto pb-px">
            {TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors whitespace-nowrap ${
                  activeTab === tab.key
                    ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-b-0 border-gray-200 dark:border-gray-700'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* ═══════════ Tab Content ═══════════ */}
      {activeTab === 'home' && <HomeTab metrics={metrics} domainCounts={domainCounts} mechanicCount={mechanicCount} />}
      {activeTab === 'tryit' && <TryItTab metrics={metrics} mechanicCount={mechanicCount} />}
      {activeTab === 'video' && <VideoTab />}
      {activeTab === 'setup' && <SetupTab />}
      {activeTab === 'architecture' && <ArchitectureTab pipelineTab={pipelineTab} setPipelineTab={setPipelineTab} />}

      {/* ═══════════ Footer ═══════════ */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p className="font-medium">
            GamED.AI: A Hierarchical Multi-Agent Framework for Automated Educational Game Generation &mdash; ACL 2026
          </p>
        </div>
      </footer>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   HOME TAB
   ═══════════════════════════════════════════════════════════════ */

function HomeTab({ metrics, domainCounts, mechanicCount }: {
  metrics: ReturnType<typeof computeAggregateMetrics>;
  domainCounts: Record<string, number>;
  mechanicCount: number;
}) {
  return (
    <>
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-8 text-center">
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-gray-900 dark:text-gray-100 mb-2">
          Transform Questions into{' '}
          <span className="bg-gradient-to-r from-blue-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
            Interactive Learning Games
          </span>
        </h1>
        <p className="text-base text-gray-500 dark:text-gray-400 max-w-2xl mx-auto mb-6">
          A hierarchical multi-agent framework that transforms instructor-provided questions into
          Bloom&apos;s-aligned educational games validated through formal mechanic contracts.
        </p>
        {/* Stats bar */}
        <div className="flex flex-wrap justify-center gap-4 text-sm">
          <StatPill label="Games" value={ACL_GAMES.length > 0 ? ACL_GAMES.length.toString() : '50'} />
          <StatPill label="Domains" value="5" />
          <StatPill label="Mechanics" value="15" />
          <StatPill label="Levels" value="3" />
          {metrics.totalGames > 0 && (
            <StatPill label="Avg Latency" value={`${metrics.avgLatencySeconds.toFixed(0)}s`} />
          )}
        </div>
      </section>

      {/* About */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-6 sm:p-8">
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-3">About GamED.AI</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-4">
            GamED.AI is a hierarchical multi-agent framework that transforms instructor-provided
            questions into fully playable, pedagogically grounded educational games validated through
            formal mechanic contracts. Built on phase-based LangGraph sub-graphs, deterministic
            Quality Gates, and structured Pydantic schemas, the system supports two template
            families encompassing <strong>15 interaction mechanics</strong> across spatial reasoning,
            procedural execution, and higher-order Bloom&apos;s Taxonomy objectives.
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed mb-4">
            Evaluated on 200 questions spanning five subject domains and all 15 mechanics, GamED.AI
            achieves a <strong>90% validation pass rate</strong> and <strong>73% token reduction</strong> over
            ReAct agents (~73,500 &rarr; ~19,900 tokens/game), demonstrating that architectural
            discipline&mdash;not model capability&mdash;is the binding variable for alignment quality.
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            Each game features dual modes: <strong>Learn</strong> mode with hints and formative
            feedback, and <strong>Test</strong> mode with timed scoring. The demonstration interface
            lets users generate games from natural language, inspect Quality Gate outputs, and browse
            50 curated games. Code, games, and evaluation datasets are publicly available.
          </p>
        </div>
      </section>

      {/* Domain showcase */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-8">
          Five Academic Domains
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {(['biology', 'history', 'cs', 'mathematics', 'linguistics'] as Domain[]).map(domain => {
            const colors = DOMAIN_COLORS[domain];
            const count = domainCounts[domain] || 10;
            return (
              <Link
                key={domain}
                href={`/acl-demo/library?domain=${domain}`}
                className={`group p-5 rounded-xl border ${colors.border} ${colors.bg} hover:shadow-lg transition-all`}
              >
                <span className="text-3xl block mb-2">{DOMAIN_ICONS[domain]}</span>
                <h3 className={`font-semibold text-sm ${colors.text} mb-1`}>
                  {DOMAIN_LABELS[domain]}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {count} games
                </p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Game mechanics */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-3">
          15 Game Mechanics
        </h2>
        <p className="text-center text-gray-500 dark:text-gray-400 max-w-xl mx-auto mb-8">
          Two template families &mdash; Interactive Diagram (10 mechanics) and Interactive Algorithm (5 mechanics) &mdash; covering spatial reasoning, procedural execution, and higher-order Bloom&apos;s objectives.
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {Object.entries(MECHANIC_LABELS).map(([key, label]) => (
            <Link
              key={key}
              href={`/acl-demo/library?mechanic=${key}`}
              className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full text-gray-700 dark:text-gray-300 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {label}
            </Link>
          ))}
        </div>
      </section>

      {/* Education levels */}
      <section className="bg-white dark:bg-gray-900 border-y border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-8">
            Three Education Levels
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <LevelCard
              level="K-12 / Middle School"
              tag="k12"
              description="Foundational concepts targeting Remember and Understand Bloom's levels with visual, interactive mechanics."
              examples={['Label plant cell parts', 'Order mitosis stages', 'Sort organisms by trophic level']}
            />
            <LevelCard
              level="Undergraduate"
              tag="undergraduate"
              description="Applied concepts targeting Apply and Analyze Bloom's levels with multi-step mechanics."
              examples={['Identify DNA replication enzymes', 'Compare French vs American Revolutions', 'Match calculus theorems']}
            />
            <LevelCard
              level="Graduate / Professional"
              tag="graduate"
              description="Advanced topics targeting Evaluate and Create Bloom's levels with complex multi-scene compositions."
              examples={['Clinical diagnosis decision tree', 'Compare numerical analysis methods', 'Navigate language acquisition stages']}
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          Browse the Game Library
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          50 curated games spanning five domains, three education levels, and 15 interaction mechanics. All games run entirely in your browser.
        </p>
        <Link
          href="/acl-demo/library"
          className="inline-block px-8 py-3 bg-gradient-to-r from-blue-600 to-violet-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-violet-700 shadow-lg hover:shadow-xl transition-all text-lg"
        >
          Open Game Library
        </Link>
      </section>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   TRY IT TAB — current landing page interactive experience
   ═══════════════════════════════════════════════════════════════ */

function TryItTab({ metrics, mechanicCount }: {
  metrics: ReturnType<typeof computeAggregateMetrics>;
  mechanicCount: number;
}) {
  const [query, setQuery] = React.useState('');
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [selectedPipeline, setSelectedPipeline] = React.useState(2); // Hierarchical
  const [selectedTemplate, setSelectedTemplate] = React.useState(0); // Interactive Diagram
  const [selectedModel, setSelectedModel] = React.useState(0); // Gemini
  const router = useRouter();

  const handleGenerate = () => {
    if (!query.trim()) return;
    setIsGenerating(true);
    // Simulate generation then navigate to observability dashboard
    setTimeout(() => {
      setIsGenerating(false);
      router.push('/acl-demo/observability');
    }, 2000);
  };

  const handleExampleClick = (text: string) => {
    setQuery(text);
  };

  return (
    <>
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-4 text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Transform Questions into{' '}
          <span className="bg-gradient-to-r from-blue-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
            Interactive Learning Games
          </span>
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xl mx-auto mb-4">
          Enter any educational question. The hierarchical DAG pipeline generates a validated,
          playable game with Bloom&apos;s-aligned mechanic contracts.
        </p>
      </section>

      {/* Chat Interface */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pb-14">
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-xl overflow-hidden">
          {/* Chat bubble */}
          <div className="p-6 pb-3">
            <div className="flex gap-3 mb-5">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-violet-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-sm text-white">{'\u{2728}'}</span>
              </div>
              <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%]">
                <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
                  Enter a natural language question or topic. The pipeline will generate a validated educational game with the selected template and mechanic. Try one of these examples:
                </p>
              </div>
            </div>
            {/* Example question pills */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 pl-11">
              {EXAMPLE_QUESTIONS.map((example, i) => (
                <button
                  key={i}
                  onClick={() => handleExampleClick(example.text)}
                  className="text-left flex items-start gap-1.5 px-3 py-2 rounded-lg text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-blue-300 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-all"
                >
                  <span className="flex-shrink-0">{example.icon}</span>
                  <span className="leading-tight">{example.text}</span>
                </button>
              ))}
            </div>
          </div>
          {/* Input area */}
          <div className="border-t border-gray-200 dark:border-gray-800 p-4">
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleGenerate(); }}
                placeholder="Describe what you want students to learn..."
                className="w-full h-[48px] pr-14 py-3 px-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 rounded-lg flex items-center justify-center cursor-pointer transition-all disabled:opacity-50"
              >
                {isGenerating ? (
                  <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                )}
              </button>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-2 mt-3">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider">Pipeline:</span>
                {['Sequential', 'ReAct', 'Hierarchical'].map((p, i) => (
                  <button
                    key={p}
                    onClick={() => setSelectedPipeline(i)}
                    className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer ${
                      i === selectedPipeline
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider">Template:</span>
                {['Interactive Diagram', 'Algorithm Game'].map((t, i) => (
                  <button
                    key={t}
                    onClick={() => setSelectedTemplate(i)}
                    className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer ${
                      i === selectedTemplate
                        ? 'bg-violet-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider">Model:</span>
                {['Gemini', 'OpenAI', 'Local'].map((m, i) => (
                  <button
                    key={m}
                    onClick={() => setSelectedModel(i)}
                    className={`text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer ${
                      i === selectedModel
                        ? 'bg-emerald-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="flex justify-center gap-3 mt-6">
          <Link
            href="/acl-demo/library"
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-violet-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-violet-700 shadow-lg hover:shadow-xl transition-all text-base"
          >
            Browse Game Library
          </Link>
        </div>
      </section>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   VIDEO TAB
   ═══════════════════════════════════════════════════════════════ */

function VideoTab() {
  const VIDEO_ID = '3aMklNAMysM';

  return (
    <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-3">
        Demo Video
      </h2>
      <p className="text-center text-gray-500 dark:text-gray-400 max-w-xl mx-auto mb-8">
        End-to-end walkthrough: natural language input, pipeline observability, Quality Gate validation, and gameplay across multiple mechanics.
      </p>
      <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-lg overflow-hidden">
        <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
          <iframe
            className="absolute inset-0 w-full h-full"
            src={`https://www.youtube.com/embed/${VIDEO_ID}`}
            title="GamED.AI Demo"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════
   GETTING STARTED TAB
   ═══════════════════════════════════════════════════════════════ */

function SetupTab() {
  const [openSection, setOpenSection] = useState<string | null>('static');

  const toggle = (key: string) => setOpenSection(prev => prev === key ? null : key);

  return (
    <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-3">
        Getting Started
      </h2>
      <p className="text-center text-gray-500 dark:text-gray-400 max-w-xl mx-auto mb-8">
        Clone the repository, install dependencies, and generate games for any educational question with your choice of model provider.
      </p>

      <div className="space-y-3">
        {/* Prerequisites */}
        <CollapsibleSection
          title="Prerequisites"
          sectionKey="prereqs"
          openSection={openSection}
          toggle={toggle}
        >
          <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
              <span><strong>Python 3.11+</strong> with pip</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
              <span><strong>Node.js 18+</strong> with npm</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
              <span><strong>Git</strong></span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
              <span><strong>API keys</strong>: Google Gemini (<code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">GOOGLE_API_KEY</code>) or OpenAI (<code className="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">OPENAI_API_KEY</code>) &mdash; only needed for game generation, not for the static demo</span>
            </li>
          </ul>
        </CollapsibleSection>

        {/* Static Demo */}
        <CollapsibleSection
          title="Static Demo (No Backend Required)"
          sectionKey="static"
          openSection={openSection}
          toggle={toggle}
        >
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
            The demo includes 50 pre-generated games as static JSON. No API keys or backend needed.
          </p>
          <CodeBlock>{`git clone <repo-url> && cd GamifyAssessment
cd frontend && npm install
npm run dev
# Visit http://localhost:3000/acl-demo`}</CodeBlock>
        </CollapsibleSection>

        {/* Full Setup */}
        <CollapsibleSection
          title="Full Setup (Backend + Frontend)"
          sectionKey="full"
          openSection={openSection}
          toggle={toggle}
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">1. Clone & setup backend</h4>
              <CodeBlock>{`git clone <repo-url> && cd GamifyAssessment
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys`}</CodeBlock>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">2. Start backend</h4>
              <CodeBlock>{`cd backend && source venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --reload --port 8000`}</CodeBlock>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">3. Start frontend</h4>
              <CodeBlock>{`cd frontend && npm install && npm run dev`}</CodeBlock>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">4. Open the app</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Visit <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">http://localhost:3000</code> &mdash; enter any educational question and watch the pipeline generate a game.
              </p>
            </div>
          </div>
        </CollapsibleSection>

        {/* CLI Pipeline */}
        <CollapsibleSection
          title="CLI Pipeline Usage"
          sectionKey="cli"
          openSection={openSection}
          toggle={toggle}
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Generate a single game</h4>
              <CodeBlock>{`cd backend && source venv/bin/activate
PYTHONPATH=. python scripts/generate_acl_demo.py \\
  --ids bio-k12-plant-cell-drag-drop`}</CodeBlock>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Generate all 50 games</h4>
              <CodeBlock>{`PYTHONPATH=. python scripts/generate_acl_demo.py`}</CodeBlock>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Dry run (list queries without generating)</h4>
              <CodeBlock>{`PYTHONPATH=. python scripts/generate_acl_demo.py --dry-run`}</CodeBlock>
            </div>
          </div>
        </CollapsibleSection>

        {/* Environment Variables */}
        <CollapsibleSection
          title="Environment Variables"
          sectionKey="env"
          openSection={openSection}
          toggle={toggle}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left px-3 py-2 text-gray-500 dark:text-gray-400 font-medium">Variable</th>
                  <th className="text-left px-3 py-2 text-gray-500 dark:text-gray-400 font-medium">Required</th>
                  <th className="text-left px-3 py-2 text-gray-500 dark:text-gray-400 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="text-gray-600 dark:text-gray-400">
                <EnvRow name="GOOGLE_API_KEY" required="Yes*" desc="Gemini API key for game generation" />
                <EnvRow name="OPENAI_API_KEY" required="Alt*" desc="OpenAI API key (alternative to Gemini)" />
                <EnvRow name="AGENT_CONFIG_PRESET" required="No" desc="Model preset (default: gemini_only)" />
                <EnvRow name="PIPELINE_PRESET" required="No" desc="Pipeline type: v4, v4_algorithm" />
              </tbody>
            </table>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              * At least one API key required for game generation. Not needed for the static demo.
            </p>
          </div>
        </CollapsibleSection>

        {/* Troubleshooting */}
        <CollapsibleSection
          title="Troubleshooting"
          sectionKey="trouble"
          openSection={openSection}
          toggle={toggle}
        >
          <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
            <div>
              <p className="font-medium text-gray-700 dark:text-gray-300 mb-1">Port 8000 in use</p>
              <CodeBlock>{`lsof -ti:8000 | xargs kill -9`}</CodeBlock>
            </div>
            <div>
              <p className="font-medium text-gray-700 dark:text-gray-300 mb-1">Port 3000 in use</p>
              <CodeBlock>{`lsof -ti:3000 | xargs kill -9`}</CodeBlock>
            </div>
            <div>
              <p className="font-medium text-gray-700 dark:text-gray-300 mb-1">Health check</p>
              <CodeBlock>{`curl http://localhost:8000/health`}</CodeBlock>
            </div>
          </div>
        </CollapsibleSection>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ARCHITECTURE TAB
   ═══════════════════════════════════════════════════════════════ */

function ArchitectureTab({ pipelineTab, setPipelineTab }: {
  pipelineTab: 'diagram' | 'algorithm';
  setPipelineTab: (v: 'diagram' | 'algorithm') => void;
}) {
  return (
    <>
      {/* Three Architectures Comparison */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-3">
          Architectural Evolution
        </h2>
        <p className="text-center text-gray-500 dark:text-gray-400 max-w-2xl mx-auto mb-8">
          Three architectures evaluated on 200 questions across all 15 mechanics. The Hierarchical DAG
          separates generation and validation into phase-bounded sub-graphs with deterministic Quality Gates.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
          {/* Sequential Pipeline */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-400" />
              <h3 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Sequential Pipeline</h3>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              {['Input Analyzer', 'Game Designer', 'Content Generator', 'Asset Generator', 'Blueprint Assembler'].map((node, i) => (
                <React.Fragment key={node}>
                  {i > 0 && <span className="text-gray-300 text-xs">&darr;</span>}
                  <div className="w-full px-3 py-1.5 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 text-center text-xs font-medium text-orange-700 dark:text-orange-300">
                    {node}
                  </div>
                </React.Fragment>
              ))}
              <span className="text-gray-300 text-xs">&darr;</span>
              <div className="w-full px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-center text-xs font-medium text-red-600 dark:text-red-400">
                Single Validator (end)
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 space-y-1">
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Agents:</span> 5 sequential</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Validation:</span> End-only</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Error handling:</span> No retry</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Parallelism:</span> None</p>
            </div>
          </div>

          {/* ReAct Agent */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
              <h3 className="font-bold text-gray-900 dark:text-gray-100 text-sm">ReAct Agent</h3>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className="w-full px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-center text-xs font-medium text-blue-700 dark:text-blue-300">
                ReAct Agent (single LLM)
              </div>
              <div className="relative w-full flex justify-center py-2">
                <svg width="80" height="40" viewBox="0 0 80 40" className="text-blue-300">
                  <path d="M40 0 C60 0, 70 20, 40 40 C10 20, 20 0, 40 0" fill="none" stroke="currentColor" strokeWidth="1.5" markerEnd="url(#arrowBlue)" />
                  <defs><marker id="arrowBlue" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto"><path d="M0,0 L6,2 L0,4" fill="currentColor"/></marker></defs>
                </svg>
                <span className="absolute top-1/2 -translate-y-1/2 right-2 text-[9px] text-blue-400 font-medium">Thought &rarr; Action &rarr; Observe</span>
              </div>
              <div className="w-full flex gap-1.5">
                {['Design', 'Content', 'Assets', 'Assemble', 'Validate'].map(tool => (
                  <div key={tool} className="flex-1 px-1 py-1 rounded bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 text-center text-[9px] font-medium text-blue-600 dark:text-blue-400">
                    {tool}
                  </div>
                ))}
              </div>
              <span className="text-gray-300 text-xs">&darr;</span>
              <div className="w-full px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-center text-xs font-medium text-red-600 dark:text-red-400">
                Self-Validation (LLM)
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 space-y-1">
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Agents:</span> 1 ReAct loop</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Validation:</span> LLM self-check</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Error handling:</span> Retry via reasoning</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Parallelism:</span> None</p>
            </div>
          </div>

          {/* Hierarchical DAG */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border-2 border-green-400 dark:border-green-600 p-5 ring-2 ring-green-100 dark:ring-green-900/30">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
              <h3 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Hierarchical DAG</h3>
              <span className="ml-auto text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">Ours</span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              {[
                { label: 'Phase 0: Context', agents: '2 parallel', color: 'green' },
                { label: 'Phase 1: Concept + QG1', agents: 'LLM + Gate', color: 'green' },
                { label: 'Phase 2: Plan + QG2', agents: 'Determ. + Gate', color: 'green' },
                { label: 'Phase 3: Content + QG3', agents: 'N parallel + Gate', color: 'green' },
                { label: 'Phase 4: Assets', agents: 'M parallel', color: 'green' },
                { label: 'Phase 5: Assembly + QG4', agents: 'Determ. + Gate', color: 'green' },
              ].map((phase, i) => (
                <React.Fragment key={phase.label}>
                  {i > 0 && <span className="text-gray-300 text-xs">&darr;</span>}
                  <div className="w-full px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 flex items-center justify-between">
                    <span className="text-xs font-medium text-green-700 dark:text-green-300">{phase.label}</span>
                    <span className="text-[9px] text-green-500 dark:text-green-400">{phase.agents}</span>
                  </div>
                </React.Fragment>
              ))}
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800 space-y-1">
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Agents:</span> 18 across 6 phases</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Validation:</span> 4 deterministic QGs</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Error handling:</span> Bounded retry per phase</p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Parallelism:</span> Send() API per scene</p>
            </div>
          </div>
        </div>
      </section>

      {/* Detailed Pipeline DAGs */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-3">
          Detailed Pipeline View
        </h2>
        <p className="text-center text-gray-500 dark:text-gray-400 max-w-2xl mx-auto mb-8">
          Full agent-level DAG for each template family.
        </p>

        {/* Pipeline tab switcher */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-gray-100 dark:bg-gray-800 rounded-xl p-1">
            <button
              onClick={() => setPipelineTab('diagram')}
              className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                pipelineTab === 'diagram'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'
              }`}
            >
              Interactive Diagram Pipeline
            </button>
            <button
              onClick={() => setPipelineTab('algorithm')}
              className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                pipelineTab === 'algorithm'
                  ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'
              }`}
            >
              Algorithm Game Pipeline
            </button>
          </div>
        </div>

        {/* Pipeline DAG */}
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-200 dark:border-gray-700 p-8 overflow-x-auto">
          {pipelineTab === 'diagram' ? (
            <V4PipelineDAG />
          ) : (
            <AlgorithmPipelineDAG />
          )}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="bg-white dark:bg-gray-900 border-y border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-8">
            Technical Stack
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left px-4 py-3 text-gray-500 dark:text-gray-400 font-medium">Component</th>
                  <th className="text-left px-4 py-3 text-gray-500 dark:text-gray-400 font-medium">Technology</th>
                  <th className="text-left px-4 py-3 text-gray-500 dark:text-gray-400 font-medium">Purpose</th>
                </tr>
              </thead>
              <tbody className="text-gray-600 dark:text-gray-400">
                <TechRow component="Backend" tech="Python / FastAPI" purpose="REST API, pipeline orchestration" />
                <TechRow component="Pipeline" tech="LangGraph" purpose="Multi-agent DAG execution with Send API" />
                <TechRow component="Frontend" tech="Next.js / React / TypeScript" purpose="Game rendering, observability UI" />
                <TechRow component="LLM" tech="Gemini 2.5 Pro" purpose="Content generation, game design, validation" />
                <TechRow component="Vision" tech="Gemini Vision / SAM3" purpose="Diagram analysis, zone detection" />
                <TechRow component="Image Gen" tech="Gemini Imagen" purpose="Educational diagram generation" />
                <TechRow component="Database" tech="SQLite" purpose="Run persistence, blueprint storage" />
                <TechRow component="State" tech="Zustand" purpose="Frontend game state management" />
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Game Template System */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center mb-8">
          Game Template System
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300">
                Diagram
              </span>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">Interactive Diagram</h3>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              Spatial and relational content targeting visual and conceptual reasoning.
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-2">10 Mechanics:</p>
            <div className="flex flex-wrap gap-1">
              {['Drag & Drop', 'Sequencing', 'Click to Identify', 'Trace Path', 'Sorting', 'Memory Match', 'Branching', 'Compare', 'Description Match', 'Hierarchical'].map(m => (
                <span key={m} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  {m}
                </span>
              ))}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300">
                Algorithm
              </span>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">Algorithm Game</h3>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              Procedural content targeting applying, analyzing, and creating objectives.
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-2">5 Mechanics:</p>
            <div className="flex flex-wrap gap-1">
              {['State Tracer', 'Bug Hunter', 'Algorithm Builder', 'Complexity Analyzer', 'Constraint Puzzle'].map(m => (
                <span key={m} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  {m}
                </span>
              ))}
            </div>
          </div>
        </div>

      </section>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SHARED HELPER COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 rounded-full shadow-sm border border-gray-200/50 dark:border-gray-700/50">
      <span className="text-gray-500 dark:text-gray-400 text-xs">{label}</span>
      <span className="font-bold text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 text-center">
      <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</div>
      <div className="text-xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  );
}

function LevelCard({ level, tag, description, examples }: {
  level: string; tag: string; description: string; examples: string[];
}) {
  return (
    <Link
      href={`/acl-demo/library?level=${tag}`}
      className="group p-6 bg-gray-50 dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all"
    >
      <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
        {level}
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">{description}</p>
      <ul className="space-y-1">
        {examples.map((ex, i) => (
          <li key={i} className="text-xs text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
            {ex}
          </li>
        ))}
      </ul>
    </Link>
  );
}

function CollapsibleSection({ title, sectionKey, openSection, toggle, children }: {
  title: string;
  sectionKey: string;
  openSection: string | null;
  toggle: (key: string) => void;
  children: React.ReactNode;
}) {
  const isOpen = openSection === sectionKey;
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
      <button
        onClick={() => toggle(sectionKey)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <span className="font-semibold text-gray-900 dark:text-gray-100 text-sm">{title}</span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-5 pb-5 border-t border-gray-100 dark:border-gray-800 pt-4">
          {children}
        </div>
      )}
    </div>
  );
}

function CodeBlock({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="relative group">
      <pre className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3 text-xs text-gray-700 dark:text-gray-300 overflow-x-auto font-mono leading-relaxed">
        {children}
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 px-2 py-1 text-[10px] font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded text-gray-500 dark:text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-gray-700 dark:hover:text-gray-200"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  );
}

function EnvRow({ name, required, desc }: { name: string; required: string; desc: string }) {
  return (
    <tr className="border-b border-gray-100 dark:border-gray-700/50">
      <td className="px-3 py-2"><code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{name}</code></td>
      <td className="px-3 py-2">{required}</td>
      <td className="px-3 py-2">{desc}</td>
    </tr>
  );
}

function TechRow({ component, tech, purpose }: { component: string; tech: string; purpose: string }) {
  return (
    <tr className="border-b border-gray-100 dark:border-gray-700/50">
      <td className="px-4 py-3 font-medium text-gray-700 dark:text-gray-300">{component}</td>
      <td className="px-4 py-3">{tech}</td>
      <td className="px-4 py-3">{purpose}</td>
    </tr>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ALGORITHM PIPELINE DAG (matches V4PipelineDAG style)
   ═══════════════════════════════════════════════════════════════ */

function ABadge({ kind, children }: { kind: 'ai' | 'valid' | 'merge' | 'determ' | 'router'; children: React.ReactNode }) {
  const styles = {
    ai:     { bg: 'bg-violet-100 dark:bg-violet-900/30', border: 'border-violet-300 dark:border-violet-700', badge: 'bg-violet-500', label: 'AI' },
    valid:  { bg: 'bg-emerald-100 dark:bg-emerald-900/30', border: 'border-emerald-300 dark:border-emerald-700', badge: 'bg-emerald-500', label: 'V' },
    merge:  { bg: 'bg-sky-100 dark:bg-sky-900/30', border: 'border-sky-300 dark:border-sky-700', badge: 'bg-sky-500', label: 'M' },
    determ: { bg: 'bg-slate-100 dark:bg-slate-900/30', border: 'border-slate-300 dark:border-slate-700', badge: 'bg-slate-500', label: 'D' },
    router: { bg: 'bg-amber-100 dark:bg-amber-900/30', border: 'border-amber-300 dark:border-amber-700', badge: 'bg-amber-500', label: 'R' },
  };
  const s = styles[kind];
  return (
    <div className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border ${s.bg} ${s.border} shadow-sm`}>
      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0 ${s.badge}`}>
        {s.label}
      </span>
      <span className="text-[12px] font-semibold text-gray-800 dark:text-gray-200 whitespace-nowrap">{children}</span>
    </div>
  );
}

function APhase({ label, color, children }: { label: string; color: string; children: React.ReactNode }) {
  return (
    <div className="relative rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white/50 dark:bg-gray-800/30 p-4 pt-3">
      <div className="absolute top-0 left-0 w-1 h-full rounded-l-xl" style={{ background: color }} />
      <div className="text-[10px] font-bold uppercase tracking-[0.15em] mb-3 pl-2" style={{ color }}>
        {label}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function ARow({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-2 flex-wrap justify-center">{children}</div>;
}

function AArrow() {
  return (
    <div className="flex justify-center -my-0.5">
      <svg width="12" height="16" viewBox="0 0 12 16" className="text-slate-400 dark:text-slate-600">
        <path d="M6 0v12M2 9l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function AHArrow() {
  return (
    <div className="flex items-center px-1">
      <svg width="24" height="12" viewBox="0 0 24 12" className="text-slate-400 dark:text-slate-600 shrink-0">
        <path d="M0 6h18M15 3l4 3-4 3" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function AFanout({ label, count }: { label: string; count?: string }) {
  return (
    <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 border border-violet-200 dark:border-violet-800">
      Send &times;{count ?? 'N'} ({label})
    </span>
  );
}

function ARetry() {
  return (
    <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800 flex items-center gap-1">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="shrink-0">
        <path d="M8 5a3 3 0 1 1-.9-2.1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        <path d="M8 1v2H6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      retry
    </span>
  );
}

function AConn() {
  return <div className="flex justify-center"><div className="w-px h-3 bg-gray-300 dark:bg-gray-600" /></div>;
}

function AlgorithmPipelineDAG() {
  return (
    <div className="w-full max-w-2xl mx-auto space-y-0">
      {/* START */}
      <div className="flex justify-center">
        <div className="px-5 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/40 border border-blue-300 dark:border-blue-700 text-[12px] font-bold text-blue-700 dark:text-blue-300 tracking-wider">
          START
        </div>
      </div>
      <AArrow />

      {/* Phase 0 */}
      <APhase label="Phase 0 — Input Analysis" color="#3b82f6">
        <ARow>
          <ABadge kind="ai">Input Enhancer</ABadge>
          <span className="text-[10px] text-gray-400 font-medium px-2">parallel</span>
          <ABadge kind="ai">DK Retriever</ABadge>
        </ARow>
        <AConn />
        <ARow>
          <ABadge kind="router">Preset Router</ABadge>
        </ARow>
      </APhase>
      <AArrow />

      {/* Phase 1 */}
      <APhase label="Phase 1 — Game Concept Design" color="#8b5cf6">
        <ARow>
          <ABadge kind="ai">Concept Designer</ABadge>
          <AHArrow />
          <ABadge kind="valid">Concept Validator</ABadge>
          <ARetry />
        </ARow>
      </APhase>
      <AArrow />

      {/* Phase 2 */}
      <APhase label="Phase 2 — Graph Building" color="#ec4899">
        <ARow>
          <ABadge kind="determ">Graph Builder</ABadge>
          <AHArrow />
          <ABadge kind="valid">Plan Validator</ABadge>
          <ARetry />
        </ARow>
      </APhase>
      <AArrow />

      {/* Phase 3 */}
      <APhase label="Phase 3 — Scene Content Generation" color="#f97316">
        <ARow>
          <div className="space-y-1 flex flex-col items-center">
            <ABadge kind="ai">Content Generator</ABadge>
            <AFanout label="per scene" count="3" />
          </div>
          <AHArrow />
          <ABadge kind="merge">Content Merge</ABadge>
        </ARow>
        <AConn />
        <ARow>
          <ABadge kind="valid">Content Validator</ABadge>
          <ARetry />
        </ARow>
      </APhase>
      <AArrow />

      {/* Phase 4 */}
      <APhase label="Phase 4 — Asset Generation" color="#ef4444">
        <ARow>
          <ABadge kind="determ">Asset Dispatcher</ABadge>
        </ARow>
        <AConn />
        <ARow>
          <div className="space-y-1 flex flex-col items-center">
            <ABadge kind="ai">Asset Worker</ABadge>
            <AFanout label="per scene" count="3" />
          </div>
          <AHArrow />
          <ABadge kind="merge">Asset Merge</ABadge>
        </ARow>
      </APhase>
      <AArrow />

      {/* Phase 5 */}
      <APhase label="Phase 5 — Blueprint Assembly" color="#22c55e">
        <ARow>
          <ABadge kind="determ">Blueprint Assembler</ABadge>
        </ARow>
      </APhase>
      <AArrow />

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
          { badge: 'bg-amber-500', label: 'Router' },
        ].map(({ badge, label }) => (
          <span key={label} className="flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
            <span className={`w-2.5 h-2.5 rounded-full ${badge}`} />
            {label}
          </span>
        ))}
        <ARetry />
        <AFanout label="parallel" count="N" />
      </div>
      <div className="text-center text-[10px] text-gray-500 dark:text-gray-400 pt-1">
        Each scene consists of tasks: State Tracer, Bug Hunter, Complexity Analyzer, Algorithm Builder, or Constraint Puzzle
      </div>
    </div>
  );
}

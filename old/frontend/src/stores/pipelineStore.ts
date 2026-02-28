import { create } from 'zustand'

interface PipelineStep {
  id: string
  step_name: string
  step_number: number
  status: 'pending' | 'processing' | 'completed' | 'error' | 'skipped'
  error_message?: string
  retry_count: number
  started_at?: string
  completed_at?: string
  validation_result?: any
}

interface PipelineState {
  processId: string | null
  questionId: string | null
  status: 'idle' | 'processing' | 'completed' | 'error'
  progress: number
  currentStep: string | null
  steps: PipelineStep[]
  visualizationId: string | null
  errorMessage: string | null
  setProcessId: (id: string | null) => void
  setQuestionId: (id: string | null) => void
  setStatus: (status: 'idle' | 'processing' | 'completed' | 'error') => void
  setProgress: (progress: number) => void
  setCurrentStep: (step: string | null) => void
  setSteps: (steps: PipelineStep[]) => void
  setVisualizationId: (id: string | null) => void
  setErrorMessage: (message: string | null) => void
  updateStep: (stepId: string, updates: Partial<PipelineStep>) => void
  reset: () => void
}

export const usePipelineStore = create<PipelineState>((set) => ({
  processId: null,
  questionId: null,
  status: 'idle',
  progress: 0,
  currentStep: null,
  steps: [],
  visualizationId: null,
  errorMessage: null,
  
  setProcessId: (id) => set({ processId: id }),
  setQuestionId: (id) => set({ questionId: id }),
  setStatus: (status) => set({ status }),
  setProgress: (progress) => set({ progress }),
  setCurrentStep: (step) => set({ currentStep: step }),
  setSteps: (steps) => set({ steps }),
  setVisualizationId: (id) => set({ visualizationId: id }),
  setErrorMessage: (message) => set({ errorMessage: message }),
  
  updateStep: (stepId, updates) =>
    set((state) => ({
      steps: state.steps.map((step) =>
        step.id === stepId ? { ...step, ...updates } : step
      ),
    })),
  
  reset: () =>
    set({
      processId: null,
      questionId: null,
      status: 'idle',
      progress: 0,
      currentStep: null,
      steps: [],
      visualizationId: null,
      errorMessage: null,
    }),
}))



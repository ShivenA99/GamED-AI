import { create } from 'zustand'

interface Question {
  id: string
  text: string
  options?: string[]
  analysis?: {
    question_type: string
    subject: string
    difficulty: string
    key_concepts: string[]
    intent: string
  }
  story?: {
    story_title: string
    story_context: string
    question_flow: any[]
  }
}

interface QuestionState {
  question: Question | null
  loading: boolean
  error: string | null
  setQuestion: (question: Question | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

export const useQuestionStore = create<QuestionState>((set) => ({
  question: null,
  loading: false,
  error: null,
  
  setQuestion: (question) => set({ question }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  reset: () =>
    set({
      question: null,
      loading: false,
      error: null,
    }),
}))



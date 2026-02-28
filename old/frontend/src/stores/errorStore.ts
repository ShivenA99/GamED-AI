import { create } from 'zustand'

interface ErrorState {
  errors: Array<{
    id: string
    message: string
    timestamp: Date
    context?: any
  }>
  addError: (message: string, context?: any) => void
  removeError: (id: string) => void
  clearErrors: () => void
}

export const useErrorStore = create<ErrorState>((set) => ({
  errors: [],
  
  addError: (message, context) =>
    set((state) => ({
      errors: [
        ...state.errors,
        {
          id: Date.now().toString(),
          message,
          timestamp: new Date(),
          context,
        },
      ],
    })),
  
  removeError: (id) =>
    set((state) => ({
      errors: state.errors.filter((error) => error.id !== id),
    })),
  
  clearErrors: () => set({ errors: [] }),
}))



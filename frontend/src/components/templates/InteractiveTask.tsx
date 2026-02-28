'use client'

import { useState } from 'react'

interface TaskConfig {
  id: string
  type: 'variable_prediction' | 'multiple_choice' | 'free_response' | 'step_analysis'
  question?: string
  description?: string
  variable?: string
  correctAnswer?: string | number
  options?: Array<{ id: string; text: string; correct: boolean }>
  hint?: string
  feedbackCorrect?: string
  feedbackIncorrect?: string
  points?: number
}

interface InteractiveTaskProps {
  task: TaskConfig
  onAnswer: (answer: any, correct: boolean) => void
  onHintRequest: () => void
  hintsUsed: number
  attempts: number
  maxAttempts?: number
  theme?: 'dark' | 'light'
}

export default function InteractiveTask({
  task,
  onAnswer,
  onHintRequest,
  hintsUsed,
  attempts,
  maxAttempts = 3,
  theme = 'dark',
}: InteractiveTaskProps) {
  const [input, setInput] = useState('')
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [showHint, setShowHint] = useState(false)
  const [feedback, setFeedback] = useState<{
    correct: boolean
    message: string
  } | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = () => {
    if (submitted) return

    let isCorrect = false
    let userAnswer: any

    switch (task.type) {
      case 'variable_prediction':
        userAnswer = input
        const correctNum = Number(task.correctAnswer)
        const userNum = Number(input)
        isCorrect = !isNaN(correctNum) && !isNaN(userNum) && correctNum === userNum
        break

      case 'multiple_choice':
        userAnswer = selectedOption
        const correctOption = task.options?.find((o) => o.correct)
        isCorrect = selectedOption === correctOption?.id
        break

      case 'free_response':
      case 'step_analysis':
        userAnswer = input
        // For free response, we could do fuzzy matching or just accept
        isCorrect = input.toLowerCase().includes(String(task.correctAnswer || '').toLowerCase())
        break
    }

    setFeedback({
      correct: isCorrect,
      message: isCorrect
        ? task.feedbackCorrect || 'Correct!'
        : task.feedbackIncorrect || 'Not quite. Try again!',
    })

    if (isCorrect) {
      setSubmitted(true)
    }

    onAnswer(userAnswer, isCorrect)
  }

  const handleHintClick = () => {
    setShowHint(true)
    onHintRequest()
  }

  const question = task.question || task.description || 'Complete this task'
  const canSubmit =
    !submitted &&
    (task.type === 'multiple_choice' ? selectedOption !== null : input.trim() !== '')

  return (
    <div
      className={`rounded-lg p-5 border-2 ${
        feedback
          ? feedback.correct
            ? 'border-green-500 bg-green-500/10'
            : 'border-orange-500 bg-orange-500/10'
          : theme === 'dark'
          ? 'border-primary-500/50 bg-primary-500/10'
          : 'border-primary-400 bg-primary-50'
      }`}
    >
      {/* Task type badge */}
      <div className="flex items-center justify-between mb-3">
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            theme === 'dark' ? 'bg-primary-500/20 text-primary-300' : 'bg-primary-100 text-primary-700'
          }`}
        >
          {task.type === 'variable_prediction' && 'Predict the Value'}
          {task.type === 'multiple_choice' && 'Choose the Answer'}
          {task.type === 'free_response' && 'Your Answer'}
          {task.type === 'step_analysis' && 'Analyze This Step'}
        </span>
        {task.points && (
          <span
            className={`text-sm font-medium ${
              theme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
            }`}
          >
            +{task.points} pts
          </span>
        )}
      </div>

      {/* Question */}
      <p
        className={`text-lg font-medium mb-4 ${
          theme === 'dark' ? 'text-gray-100' : 'text-gray-800'
        }`}
      >
        {question}
        {task.variable && (
          <code
            className={`ml-2 px-2 py-1 rounded text-base ${
              theme === 'dark' ? 'bg-gray-700 text-pink-400' : 'bg-gray-200 text-pink-600'
            }`}
          >
            {task.variable}
          </code>
        )}
      </p>

      {/* Input based on type */}
      {(task.type === 'variable_prediction' || task.type === 'free_response' || task.type === 'step_analysis') && (
        <div className="mb-4">
          {task.type === 'variable_prediction' ? (
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter the value..."
              disabled={submitted}
              className={`
                w-full p-3 rounded-lg border-2 font-mono text-lg
                focus:outline-none focus:ring-2 focus:ring-primary-500
                ${submitted ? 'opacity-70 cursor-not-allowed' : ''}
                ${
                  theme === 'dark'
                    ? 'bg-gray-800 border-gray-600 text-white placeholder-gray-500'
                    : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
                }
              `}
              onKeyDown={(e) => e.key === 'Enter' && canSubmit && handleSubmit()}
            />
          ) : (
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your answer..."
              disabled={submitted}
              rows={3}
              className={`
                w-full p-3 rounded-lg border-2 resize-none
                focus:outline-none focus:ring-2 focus:ring-primary-500
                ${submitted ? 'opacity-70 cursor-not-allowed' : ''}
                ${
                  theme === 'dark'
                    ? 'bg-gray-800 border-gray-600 text-white placeholder-gray-500'
                    : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
                }
              `}
            />
          )}
        </div>
      )}

      {/* Multiple choice options */}
      {task.type === 'multiple_choice' && task.options && (
        <div className="space-y-2 mb-4">
          {task.options.map((option) => {
            const isSelected = selectedOption === option.id
            const showCorrect = feedback && option.correct
            const showWrong = feedback && isSelected && !option.correct

            return (
              <button
                key={option.id}
                onClick={() => !submitted && setSelectedOption(option.id)}
                disabled={submitted}
                className={`
                  w-full p-3 rounded-lg border-2 text-left transition-all
                  ${submitted ? 'cursor-not-allowed' : 'cursor-pointer hover:scale-[1.01]'}
                  ${
                    showCorrect
                      ? 'border-green-500 bg-green-500/20'
                      : showWrong
                      ? 'border-red-500 bg-red-500/20'
                      : isSelected
                      ? theme === 'dark'
                        ? 'border-primary-500 bg-primary-500/20'
                        : 'border-primary-500 bg-primary-100'
                      : theme === 'dark'
                      ? 'border-gray-600 bg-gray-800 hover:border-gray-500'
                      : 'border-gray-300 bg-white hover:border-gray-400'
                  }
                `}
              >
                <span
                  className={`flex items-center ${
                    theme === 'dark' ? 'text-gray-100' : 'text-gray-800'
                  }`}
                >
                  <span
                    className={`
                      w-6 h-6 rounded-full border-2 flex items-center justify-center mr-3 text-sm font-medium
                      ${
                        isSelected
                          ? 'border-primary-500 bg-primary-500 text-white'
                          : theme === 'dark'
                          ? 'border-gray-500'
                          : 'border-gray-400'
                      }
                    `}
                  >
                    {isSelected && (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </span>
                  {option.text}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* Hint */}
      {task.hint && !showHint && !feedback && (
        <button
          onClick={handleHintClick}
          className={`text-sm mb-4 flex items-center ${
            theme === 'dark' ? 'text-yellow-400 hover:text-yellow-300' : 'text-yellow-600 hover:text-yellow-700'
          }`}
        >
          <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd"
            />
          </svg>
          Need a hint? ({hintsUsed} used)
        </button>
      )}

      {showHint && task.hint && (
        <div
          className={`p-3 rounded-lg mb-4 ${
            theme === 'dark' ? 'bg-yellow-500/10 border border-yellow-500/30' : 'bg-yellow-50 border border-yellow-200'
          }`}
        >
          <p
            className={`text-sm flex items-start ${
              theme === 'dark' ? 'text-yellow-300' : 'text-yellow-700'
            }`}
          >
            <svg className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
            </svg>
            {task.hint}
          </p>
        </div>
      )}

      {/* Feedback */}
      {feedback && (
        <div
          className={`p-3 rounded-lg mb-4 ${
            feedback.correct
              ? 'bg-green-500/20 border border-green-500/30'
              : 'bg-red-500/20 border border-red-500/30'
          }`}
        >
          <p
            className={`text-sm flex items-start font-medium ${
              feedback.correct ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {feedback.correct ? (
              <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            {feedback.message}
          </p>
        </div>
      )}

      {/* Submit button */}
      {!submitted && (
        <div className="flex items-center justify-between">
          <span
            className={`text-xs ${theme === 'dark' ? 'text-gray-500' : 'text-gray-400'}`}
          >
            Attempts: {attempts}/{maxAttempts}
          </span>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`
              px-6 py-2 rounded-lg font-medium transition-all
              ${
                canSubmit
                  ? 'bg-primary-500 text-white hover:bg-primary-600 active:scale-95'
                  : theme === 'dark'
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }
            `}
          >
            Submit
          </button>
        </div>
      )}

      {/* Submitted success */}
      {submitted && (
        <div className="text-center">
          <span className="text-green-400 font-medium flex items-center justify-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            Task Complete! Click Next Step to continue.
          </span>
        </div>
      )}
    </div>
  )
}

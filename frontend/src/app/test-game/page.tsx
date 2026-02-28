'use client'

import StateTracerCodeGame from '@/components/templates/StateTracerCodeGame'

// Sample blueprint for testing
const sampleBlueprint = {
  templateType: "STATE_TRACER_CODE",
  title: "Code Detective: Trace Factorial Calculation",
  narrativeIntro: "Trace the execution of this Python function step-by-step to understand how variables change during its operation.",
  code: `def factorial(n):
    result = 1
    for i in range(1, n+1):
        result = result * i
    return result

factorial(4)`,
  language: "python",
  key_concepts: [
    "Variable Assignment",
    "For Loop",
    "Range Function",
    "Factorial Calculation"
  ],
  learningObjectives: [
    "Trace the execution of a given Python function step-by-step",
    "Identify how variables change during the execution of a loop"
  ],
  steps: [
    {
      index: 0,
      lineNumber: 1,
      description: "Function `factorial` is defined with parameter `n`.",
      expectedVariables: {}
    },
    {
      index: 1,
      lineNumber: 2,
      description: "Variable `result` is assigned the value of 1.",
      expectedVariables: {
        result: 1
      }
    },
    {
      index: 2,
      lineNumber: 3,
      description: "For loop starts with `i` in range from 1 to n+1 (5).",
      expectedVariables: {
        result: 1
      }
    },
    {
      index: 3,
      lineNumber: 4,
      description: "First iteration: i = 1, result = 1 * 1 = 1.",
      expectedVariables: {
        i: 1,
        result: 1
      }
    },
    {
      index: 4,
      lineNumber: 4,
      description: "Second iteration: i = 2, result = 1 * 2 = 2.",
      expectedVariables: {
        i: 2,
        result: 2
      }
    },
    {
      index: 5,
      lineNumber: 4,
      description: "Third iteration: i = 3, result = 2 * 3 = 6.",
      expectedVariables: {
        i: 3,
        result: 6
      }
    },
    {
      index: 6,
      lineNumber: 4,
      description: "Fourth iteration: i = 4, result = 6 * 4 = 24. Loop ends.",
      expectedVariables: {
        i: 4,
        result: 24
      }
    },
    {
      index: 7,
      lineNumber: 5,
      description: "Function returns the value of `result`, which is 24.",
      expectedVariables: {
        result: 24
      }
    }
  ],
  tasks: [
    {
      id: "task_0",
      type: "variable_prediction" as const,
      question: "What is the value of result after the first iteration?",
      variable: "result",
      correctAnswer: 1,
      hint: "In the first iteration, i = 1, so result = 1 * 1",
      feedbackCorrect: "Correct! result = 1 * 1 = 1",
      feedbackIncorrect: "Remember: in the first iteration, i = 1, so result = 1 * 1 = 1",
      points: 15,
      insertAfterStep: 3
    },
    {
      id: "task_1",
      type: "variable_prediction" as const,
      question: "What is the value of result after all iterations complete?",
      variable: "result",
      correctAnswer: 24,
      hint: "4! = 4 * 3 * 2 * 1",
      feedbackCorrect: "Excellent! 4! = 24",
      feedbackIncorrect: "Hint: 4! = 4 * 3 * 2 * 1 = 24",
      points: 20,
      insertAfterStep: 6
    }
  ],
  animationCues: {
    line_highlight_animation: {
      duration: 500,
      effect: "pulse_glow",
      color: "#FFD700"
    },
    variable_update_animation: {
      duration: 800,
      effect: "flip_fade",
      easing: "ease-in-out"
    }
  },
  feedbackMessages: {
    perfect: "Excellent! You traced the factorial function perfectly!",
    good: "Good job! You understand how the loop accumulates the result.",
    needsPractice: "Keep practicing! Pay attention to how result changes in each iteration."
  }
}

export default function TestGamePage() {
  return (
    <div className="min-h-screen bg-gray-950 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-6">
          <a
            href="/"
            className="text-primary-400 hover:text-primary-300 flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Home
          </a>
        </div>

        <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-yellow-400 text-sm">
            This is a test page showing the new STATE_TRACER_CODE component with a sample factorial blueprint.
          </p>
        </div>

        <StateTracerCodeGame
          blueprint={sampleBlueprint}
          onComplete={(score) => {
            alert(`Game Complete!\nScore: ${score.earned}/${score.possible}\nTasks: ${score.tasksCompleted}\nMax Streak: ${score.maxStreak}`)
          }}
          sessionId="test-session"
          theme="dark"
        />
      </div>
    </div>
  )
}

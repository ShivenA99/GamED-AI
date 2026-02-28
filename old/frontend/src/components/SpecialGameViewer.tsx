'use client'

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Trophy, Home, RotateCcw } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface SpecialGameViewerProps {
  htmlContent: string
  onComplete: () => void
}

export function SpecialGameViewer({ htmlContent, onComplete }: SpecialGameViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const styleRef = useRef<HTMLStyleElement | null>(null)
  const [showGreatPage, setShowGreatPage] = useState(false)
  const router = useRouter()

  useEffect(() => {
    if (!containerRef.current) return

    // Parse the HTML to extract CSS and body content
    const parser = new DOMParser()
    const doc = parser.parseFromString(htmlContent, 'text/html')
    
    // Extract CSS from <style> tag
    const styleElement = doc.querySelector('style')
    const cssContent = styleElement?.textContent || ''
    
    // Extract body content
    const bodyContent = doc.body.innerHTML

    // Create a style element and inject CSS
    if (cssContent) {
      const styleEl = document.createElement('style')
      styleEl.id = 'special-game-styles'
      styleEl.textContent = cssContent
      document.head.appendChild(styleEl)
      styleRef.current = styleEl
    }

    // Extract and execute scripts separately
    const scripts = doc.querySelectorAll('script')
    const scriptContents: string[] = []
    scripts.forEach(script => {
      if (script.textContent) {
        scriptContents.push(script.textContent)
      }
    })

    // Remove scripts from body content before injecting
    const bodyWithoutScripts = doc.body.cloneNode(true) as HTMLElement
    bodyWithoutScripts.querySelectorAll('script').forEach(script => script.remove())
    containerRef.current.innerHTML = bodyWithoutScripts.innerHTML

    // Execute scripts after a brief delay to ensure DOM is ready
    setTimeout(() => {
      scriptContents.forEach(scriptContent => {
        try {
          // Execute script in global scope so onclick handlers work
          const scriptEl = document.createElement('script')
          scriptEl.textContent = scriptContent
          // Append to document body so it executes in global scope
          document.body.appendChild(scriptEl)
          // Script executes immediately when appended
          // Remove after a brief delay
          setTimeout(() => {
            if (scriptEl.parentNode) {
              scriptEl.parentNode.removeChild(scriptEl)
            }
          }, 100)
        } catch (e) {
          console.warn('Error executing script:', e)
        }
      })
      
      // Ensure generateNewChallenge is called if it exists
      setTimeout(() => {
        if (typeof (window as any).generateNewChallenge === 'function') {
          try {
            ;(window as any).generateNewChallenge()
          } catch (e) {
            console.warn('Error calling generateNewChallenge:', e)
          }
        }
      }, 200)
    }, 50)

    // Wait for scripts to execute, then override checkAnswer function
    const overrideCheckAnswer = () => {
      // Override the checkAnswer function globally
      if (typeof (window as any).checkAnswer === 'function') {
        const originalCheckAnswer = (window as any).checkAnswer
        ;(window as any).checkAnswer = function() {
          // Call original function first to show feedback
          try {
            originalCheckAnswer()
          } catch (e) {
            console.warn('Error calling original checkAnswer:', e)
          }
          // Then show Great page after a short delay
          setTimeout(() => {
            setShowGreatPage(true)
          }, 1500)
        }
        return true
      }
      return false
    }

    // Try multiple times to catch the function after scripts execute
    let attempts = 0
    const tryOverride = setInterval(() => {
      if (overrideCheckAnswer() || attempts >= 10) {
        clearInterval(tryOverride)
      }
      attempts++
    }, 100)

    // Intercept submit button clicks - use event delegation
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      const button = target.closest('button')
      
      if (button) {
        const buttonText = button.textContent?.toLowerCase() || ''
        const hasOnclick = button.getAttribute('onclick')
        
        // Check if it's a submit button
        if (buttonText.includes('submit') || 
            hasOnclick?.includes('checkAnswer') ||
            button.classList.contains('submit-btn')) {
          // Let the original function run first (if any)
          // Then show Great page after feedback is shown
          setTimeout(() => {
            setShowGreatPage(true)
          }, 2000)
        }
      }
    }

    // Intercept form submissions
    const handleFormSubmit = (e: Event) => {
      e.preventDefault()
      e.stopPropagation()
      setShowGreatPage(true)
    }

    // Use capture phase to catch events early
    containerRef.current.addEventListener('click', handleClick, true)
    const forms = containerRef.current.querySelectorAll('form')
    forms.forEach(form => {
      form.addEventListener('submit', handleFormSubmit, true)
    })

    return () => {
      clearInterval(tryOverride)
      if (styleRef.current && document.head.contains(styleRef.current)) {
        document.head.removeChild(styleRef.current)
      }
      if (containerRef.current) {
        containerRef.current.removeEventListener('click', handleClick, true)
        const forms = containerRef.current.querySelectorAll('form')
        forms.forEach(form => {
          form.removeEventListener('submit', handleFormSubmit, true)
        })
      }
    }
  }, [htmlContent])

  const handleReset = () => {
    setShowGreatPage(false)
    // Reload the page to reset the game
    window.location.reload()
  }

  if (showGreatPage) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="fixed inset-0 bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex items-center justify-center z-50"
      >
        <div className="bg-white rounded-3xl shadow-2xl p-12 max-w-md mx-4 text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="mb-6"
          >
            <Trophy className="w-24 h-24 text-yellow-500 mx-auto" />
          </motion.div>
          
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            🎉 Great Job! 🎉
          </h2>
          
          <p className="text-xl text-gray-700 mb-8">
            You've completed the interactive game successfully!
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => router.push('/app')}
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg"
            >
              <Home className="w-5 h-5" />
              Home
            </button>
            
            <button
              onClick={handleReset}
              className="px-8 py-4 rounded-xl border-2 border-gray-300 text-gray-700 font-semibold text-lg hover:bg-gray-50 transition-all flex items-center justify-center gap-2"
            >
              <RotateCcw className="w-5 h-5" />
              Play Again
            </button>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="fixed inset-0 bg-[#FFFEF9] z-50 overflow-auto">
      <div 
        ref={containerRef}
        className="min-h-screen w-full"
        style={{
          fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
          padding: '20px'
        }}
      />
    </div>
  )
}


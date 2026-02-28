'use client'

import { useEffect, useRef } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface CodeDisplayProps {
  code: string
  language: string
  currentLine: number
  executedLines: number[]
  theme?: 'dark' | 'light'
  onLineClick?: (lineNumber: number) => void
  showLineNumbers?: boolean
}

export default function CodeDisplay({
  code,
  language,
  currentLine,
  executedLines,
  theme = 'dark',
  onLineClick,
  showLineNumbers = true,
}: CodeDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const currentLineRef = useRef<HTMLTableRowElement>(null)

  // Scroll current line into view
  useEffect(() => {
    if (currentLineRef.current) {
      currentLineRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [currentLine])

  const syntaxTheme = theme === 'dark' ? vscDarkPlus : oneLight

  // Split code into lines for custom rendering
  const lines = code.split('\n')

  return (
    <div
      ref={containerRef}
      className={`rounded-lg overflow-hidden ${
        theme === 'dark' ? 'bg-[#1e1e1e]' : 'bg-[#fafafa]'
      }`}
    >
      {/* Header */}
      <div
        className={`px-4 py-2 flex items-center justify-between ${
          theme === 'dark' ? 'bg-[#2d2d2d]' : 'bg-[#e8e8e8]'
        }`}
      >
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
        </div>
        <span
          className={`text-sm font-mono ${
            theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
          }`}
        >
          {language}
        </span>
      </div>

      {/* Code content */}
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, index) => {
              const lineNumber = index + 1
              const isCurrentLine = lineNumber === currentLine
              const isExecuted = executedLines.includes(lineNumber)

              return (
                <tr
                  key={index}
                  ref={isCurrentLine ? currentLineRef : null}
                  onClick={() => onLineClick?.(lineNumber)}
                  className={`
                    ${onLineClick ? 'cursor-pointer' : ''}
                    transition-all duration-200
                    ${
                      isCurrentLine
                        ? theme === 'dark'
                          ? 'bg-yellow-500/20 border-l-4 border-yellow-400'
                          : 'bg-yellow-200/50 border-l-4 border-yellow-500'
                        : isExecuted
                        ? theme === 'dark'
                          ? 'bg-green-500/10'
                          : 'bg-green-100/50'
                        : ''
                    }
                    ${
                      onLineClick && !isCurrentLine
                        ? theme === 'dark'
                          ? 'hover:bg-white/5'
                          : 'hover:bg-gray-100'
                        : ''
                    }
                  `}
                >
                  {/* Line number */}
                  {showLineNumbers && (
                    <td
                      className={`
                        select-none text-right px-4 py-0 font-mono text-sm
                        ${
                          theme === 'dark'
                            ? 'text-gray-500 border-r border-gray-700'
                            : 'text-gray-400 border-r border-gray-300'
                        }
                        ${isCurrentLine ? 'font-bold' : ''}
                      `}
                      style={{ width: '50px' }}
                    >
                      {lineNumber}
                    </td>
                  )}

                  {/* Code line */}
                  <td className="pl-4 pr-4 py-0 whitespace-pre font-mono text-sm">
                    <SyntaxHighlighter
                      language={language}
                      style={syntaxTheme}
                      customStyle={{
                        margin: 0,
                        padding: '4px 0',
                        background: 'transparent',
                        fontSize: '14px',
                      }}
                      PreTag="span"
                    >
                      {line || ' '}
                    </SyntaxHighlighter>
                  </td>

                  {/* Current line indicator */}
                  {isCurrentLine && (
                    <td
                      className="w-8"
                      style={{ width: '32px' }}
                    >
                      <svg
                        className="w-5 h-5 text-yellow-400 animate-pulse"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

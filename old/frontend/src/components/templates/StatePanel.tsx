'use client'

import { motion } from 'framer-motion'
import { Code, Database, Lightbulb } from 'lucide-react'

interface StatePanelProps {
  variables?: Record<string, any>
  code?: string
  explanation?: string
  title?: string
}

export function StatePanel({ 
  variables = {}, 
  code, 
  explanation,
  title = "Algorithm State"
}: StatePanelProps) {
  return (
    <div className="w-full space-y-4">
      <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
        <Database className="w-5 h-5" />
        {title}
      </h3>

      {/* Variables */}
      {Object.keys(variables).length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(variables).map(([key, value]) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col"
              >
                <span className="text-xs text-gray-500 uppercase tracking-wide">{key}</span>
                <span className="text-lg font-mono font-semibold text-gray-800">
                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Code */}
      {code && (
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <Code className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-400 uppercase">Code</span>
          </div>
          <pre className="text-sm text-green-400 font-mono overflow-x-auto">
            {code}
          </pre>
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-blue-50 rounded-lg p-4 border border-blue-200"
        >
          <div className="flex items-start gap-2">
            <Lightbulb className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-gray-700">{explanation}</p>
          </div>
        </motion.div>
      )}
    </div>
  )
}


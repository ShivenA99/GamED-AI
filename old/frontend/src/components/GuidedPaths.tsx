'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'

const tabs = ['Math', 'CS & Programming', 'Data Analysis', 'Science']

export default function GuidedPaths() {
  const [activeTab, setActiveTab] = useState('Math')

  return (
    <section className="py-24 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-black mb-4">
            Guided paths for every journey
          </h2>
        </motion.div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2 rounded-full transition-all ${
                activeTab === tab
                  ? 'bg-white text-black shadow-md'
                  : 'text-muted-gray hover:text-black'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Demo Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8 max-w-4xl mx-auto"
        >
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="font-mono text-sm space-y-2">
                <div className="text-deep-purple">repeat</div>
                <div className="text-body-gray ml-4">while condition:</div>
                <div className="text-body-gray ml-8">move()</div>
                <div className="text-body-gray ml-8">turn()</div>
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-center">
              <div className="w-full h-32 bg-gradient-to-br from-vibrant-blue to-deep-purple rounded-lg" />
            </div>
          </div>
          <div className="mt-4 text-center">
            <button className="text-sm text-vibrant-blue font-semibold">
              Quadratic functions
            </button>
          </div>
        </motion.div>
      </div>
    </section>
  )
}


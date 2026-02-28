'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Search, Loader2 } from 'lucide-react'
import axios from 'axios'
import Header from '@/components/Header'

const questionSuggestions = [
  {
    title: 'Maximum Depth of Binary Tree (Recursion – Easy)',
    problem: 'Given the root of a binary tree, return its maximum depth — the number of nodes along the longest path from the root down to a leaf node.',
    example: 'Input: root = [3,9,20,null,null,15,7]\nOutput: 3',
    question: 'Which traversal is best suited for this problem?',
    options: ['A. Inorder', 'B. Preorder ✅', 'C. Postorder', 'D. Level Order']
  },
  {
    title: 'Water and Salt Solution',
    problem: 'How much water must be added to 20 liters of a 35% salt solution to make it 20%?',
    example: '',
    question: '',
    options: []
  }
]

export default function SearchPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [processingIndex, setProcessingIndex] = useState<number | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  const formatQuestionText = (suggestion: typeof questionSuggestions[0]): string => {
    let text = `${suggestion.title}\n\n`
    
    if (suggestion.problem) {
      text += `Problem:\n${suggestion.problem}\n\n`
    }
    
    if (suggestion.example) {
      text += `Example:\n${suggestion.example}\n\n`
    }
    
    if (suggestion.question) {
      text += `Question:\n${suggestion.question}\n\n`
    }
    
    if (suggestion.options.length > 0) {
      text += `Options:\n${suggestion.options.join('\n')}\n`
    }
    
    return text
  }

  const uploadQuestion = async (questionText: string, filename: string) => {
    try {
      // Create a text file blob
      const blob = new Blob([questionText], { type: 'text/plain' })
      const file = new File([blob], filename, { type: 'text/plain' })
      
      // Create FormData
      const formData = new FormData()
      formData.append('file', file)
      
      // Upload the file
      const uploadResponse = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      
      const questionId = uploadResponse.data.question_id
      
      // Clear old visualization data when uploading a new question
      localStorage.removeItem('visualizationId')
      localStorage.removeItem('processId')
      
      // Store the question ID and text for preview
      localStorage.setItem('questionId', questionId)
      localStorage.setItem('questionText', questionText)
      
      // Navigate to preview page (user will click "Start Interactive Game" button there)
      router.push('/app/preview')
    } catch (error: any) {
      console.error('Failed to upload question:', error)
      alert(error.response?.data?.detail || 'Failed to upload question. Please try again.')
      throw error
    }
  }

  const handleSuggestionClick = async (suggestion: typeof questionSuggestions[0], index: number) => {
    if (processingIndex !== null || isSearching) return // Prevent multiple clicks
    
    setProcessingIndex(index)
    
    try {
      // Format the question text
      const questionText = formatQuestionText(suggestion)
      const filename = `${suggestion.title.replace(/\s+/g, '_')}.txt`
      
      await uploadQuestion(questionText, filename)
    } catch (error) {
      setProcessingIndex(null)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim() || processingIndex !== null || isSearching) return
    
    setIsSearching(true)
    
    try {
      // Use the search query as the question text
      const questionText = searchQuery.trim()
      const filename = `question_${Date.now()}.txt`
      
      await uploadQuestion(questionText, filename)
    } catch (error) {
      setIsSearching(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9]">
      <Header />
      <div className="pt-32 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          {/* Title with emoji */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="text-4xl md:text-5xl font-bold text-black mb-2">
              Hey Mate ? 👋
            </h1>
          </motion.div>

          {/* Search Bar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-8"
          >
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="See code turning into game... ✨"
                disabled={isSearching || processingIndex !== null}
                className="w-full pl-12 pr-16 py-4 rounded-full border-2 border-gray-300 focus:border-brilliant-green focus:outline-none text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {isSearching ? (
                <Loader2 className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 animate-spin text-brilliant-green" />
              ) : (
                <button
                  onClick={handleSearch}
                  disabled={!searchQuery.trim() || processingIndex !== null}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-brilliant-green transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  aria-label="Search"
                >
                  <Search className="w-5 h-5" />
                </button>
              )}
            </div>
          </motion.div>

          {/* Quick Suggestions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="mb-12"
          >
            <div className="flex gap-4 flex-wrap justify-center">
              <button
                onClick={() => {
                  setSearchQuery('Demonstrate entry and exit of elements in stacks and queues')
                  handleSearch()
                }}
                disabled={isSearching || processingIndex !== null}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-full font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                📚 Demonstrate entry and exit of elements in stacks and queues
              </button>
              <button
                onClick={() => {
                  setSearchQuery('Show BFS in graph.')
                  handleSearch()
                }}
                disabled={isSearching || processingIndex !== null}
                className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-600 text-white rounded-full font-semibold hover:from-purple-600 hover:to-pink-700 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                🗺️ Show BFS in graph.
              </button>
            </div>
          </motion.div>

          {/* Question Suggestions */}
          <div className="space-y-4">
            {questionSuggestions.map((suggestion, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + index * 0.1 }}
                onClick={() => handleSuggestionClick(suggestion, index)}
                className={`bg-white rounded-2xl shadow-md border border-gray-200 p-6 hover:shadow-lg transition-shadow cursor-pointer ${
                  processingIndex === index ? 'opacity-75 pointer-events-none' : ''
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-black mb-2">
                      {suggestion.title}
                    </h3>
                    {processingIndex === index && (
                      <Loader2 className="w-5 h-5 animate-spin text-brilliant-green" />
                    )}
                  </div>
                  <div className="text-sm text-body-gray">
                    {suggestion.problem && (
                      <p className="line-clamp-1">
                        <span className="font-semibold">Problem:</span> {suggestion.problem}
                      </p>
                    )}
                    {suggestion.example && (
                      <p className="line-clamp-1 mt-1">
                        <span className="font-semibold">Example:</span> {suggestion.example}
                      </p>
                    )}
                    {suggestion.question && (
                      <p className="line-clamp-1 mt-1">
                        <span className="font-semibold">🔍 Question:</span> {suggestion.question}
                      </p>
                    )}
                    {suggestion.options.length > 0 && (
                      <p className="line-clamp-1 mt-1">
                        {suggestion.options.join(' ')}
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}


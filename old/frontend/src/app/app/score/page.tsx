'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Trophy, Star, RotateCcw, Home } from 'lucide-react'
import Link from 'next/link'
import Header from '@/components/Header'

export default function ScorePage() {
  const router = useRouter()
  const [score, setScore] = useState(0)
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [percentage, setPercentage] = useState(0)

  useEffect(() => {
    const finalScore = localStorage.getItem('finalScore')
    const total = localStorage.getItem('totalQuestions')

    if (finalScore && total) {
      const scoreNum = parseInt(finalScore)
      const totalNum = parseInt(total)
      setScore(scoreNum)
      setTotalQuestions(totalNum)
      setPercentage(Math.round((scoreNum / totalNum) * 100))
    } else {
      router.push('/app')
    }
  }, [router])

  const getScoreMessage = () => {
    if (percentage === 100) return "Perfect! You're a master!"
    if (percentage >= 80) return 'Excellent work!'
    if (percentage >= 60) return 'Good job! Keep practicing.'
    return "Nice try! You're learning!"
  }

  const getScoreColor = () => {
    if (percentage === 100) return 'text-golden-yellow'
    if (percentage >= 80) return 'text-brilliant-green'
    if (percentage >= 60) return 'text-vibrant-blue'
    return 'text-warm-orange'
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-[#FFFEF9]">
      <Header />
      <div className="pt-32 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            {percentage === 100 ? (
              <Trophy className="w-24 h-24 text-golden-yellow mx-auto mb-4" />
            ) : (
              <Star className="w-24 h-24 text-brilliant-green mx-auto mb-4" />
            )}
            <h1 className="text-5xl md:text-6xl font-bold text-black mb-4">
              Game Complete!
            </h1>
            <p className="text-2xl text-body-gray mb-8">{getScoreMessage()}</p>
          </motion.div>

          {/* Score Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl shadow-lg border border-gray-200 p-12 mb-8"
          >
            <div className="mb-8">
              <div className={`text-7xl font-bold mb-4 ${getScoreColor()}`}>
                {percentage}%
              </div>
              <div className="text-3xl font-semibold text-black mb-2">
                {score} / {totalQuestions}
              </div>
              <p className="text-body-gray">Correct Answers</p>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-gray-200 rounded-full h-4 mb-8">
              <motion.div
                className={`h-4 rounded-full ${
                  percentage === 100
                    ? 'bg-golden-yellow'
                    : percentage >= 80
                    ? 'bg-brilliant-green'
                    : percentage >= 60
                    ? 'bg-vibrant-blue'
                    : 'bg-warm-orange'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${percentage}%` }}
                transition={{ duration: 1, delay: 0.5 }}
              />
            </div>
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <button
              onClick={() => router.push('/app')}
              className="px-8 py-4 rounded-full bg-brilliant-green text-white font-semibold text-lg hover:scale-105 transition-transform flex items-center justify-center gap-2"
            >
              <RotateCcw className="w-5 h-5" />
              Try Another Question
            </button>
            <Link
              href="/"
              className="px-8 py-4 rounded-full border-2 border-gray-300 text-black font-semibold text-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
            >
              <Home className="w-5 h-5" />
              Back to Home
            </Link>
          </motion.div>
        </div>
      </div>
    </div>
  )
}


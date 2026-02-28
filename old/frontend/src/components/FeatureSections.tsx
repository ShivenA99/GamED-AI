'use client'

import { motion } from 'framer-motion'
import { CheckCircle2, Target, Trophy, BookOpen, Zap, MousePointer2 } from 'lucide-react'

const features = [
  {
    title: 'Concepts that click',
    description: 'Interactive lessons make even complex ideas easy to grasp. Instant, custom feedback accelerates your understanding.',
    bgGradient: 'from-[#FFFEF9] to-[#F5F3FF]',
    layout: 'left-text',
    visual: <div className="w-full h-96 bg-white rounded-lg flex items-center justify-center">
      <div className="relative">
        <motion.div 
          className="w-32 h-32 border-4 border-vibrant-blue rounded-full cursor-pointer"
          whileTap={{ scale: 0.9 }}
          whileHover={{ scale: 1.05 }}
          transition={{ type: "spring", stiffness: 400, damping: 17 }}
        />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
          <MousePointer2 className="w-8 h-8 text-vibrant-blue" />
        </div>
      </div>
    </div>
  },
  {
    title: 'Learn at your level',
    description: 'Brush up on the basics or learn new skills. Designed for learners ages 13 to 113.',
    bgGradient: 'from-light-lavender to-[#E9D5FF]',
    layout: 'right-text',
    badge: 'FOR YOU',
    visual: <div className="w-full h-96 bg-white rounded-lg flex items-center justify-center relative">
      <div className="flex flex-col gap-4">
        <div className="w-24 h-24 bg-deep-purple rounded-lg" />
        <div className="w-24 h-24 bg-deep-purple rounded-lg opacity-60" />
        <div className="w-24 h-24 bg-deep-purple rounded-lg opacity-40" />
      </div>
      <div className="absolute top-4 left-4 bg-deep-purple text-white px-3 py-1 rounded-full text-xs font-semibold">
        FOR YOU
      </div>
    </div>
  },
  {
    title: 'Stay motivated',
    description: 'Finish every day smarter with engaging lessons, competitive features, and daily encouragement.',
    bgGradient: 'from-peach-start to-peach-end',
    layout: 'left-text',
    visual: <div className="w-full h-96 bg-white rounded-lg flex items-center justify-center gap-4 relative">
      {['T', 'W', 'Th'].map((day, i) => (
        <div key={day} className={`w-16 h-16 rounded-full flex items-center justify-center ${i < 2 ? 'bg-brilliant-green' : 'bg-gray-200'}`}>
          <Zap className={`w-8 h-8 ${i < 2 ? 'text-white' : 'text-gray-400'}`} />
        </div>
      ))}
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-4 flex items-center gap-2">
        <Trophy className="w-6 h-6 text-golden-yellow" />
        <span className="text-sm font-semibold">Reach your daily goal!</span>
      </div>
    </div>
  },
  {
    title: 'Guided bite-sized lessons',
    description: 'Stay on track, see your progress, and build your problem solving skills one concept at a time.',
    bgGradient: 'from-[#FFE4D9] to-[#FFD4C4]',
    layout: 'right-text',
    visual: <div className="w-full h-96 bg-white rounded-lg flex items-center justify-center relative">
      <div className="relative">
        <div className="w-32 h-32 border-4 border-warm-orange rounded-full" />
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <CheckCircle2 className="w-16 h-16 text-brilliant-green" />
        </div>
      </div>
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-3">
        <div className="text-sm font-semibold mb-1">Exponential Growth</div>
        <div className="flex items-center gap-1 text-xs text-muted-gray">
          <BookOpen className="w-4 h-4" />
          <span>15 minutes</span>
        </div>
      </div>
    </div>
  },
  {
    title: 'More effective. More fun.',
    description: "Brilliant's interactive approach teaches you to think, not memorize.",
    bgGradient: 'from-mint-green to-[#B8E6C9]',
    layout: 'left-text',
    visual: <div className="w-full h-96 bg-white rounded-lg flex items-center justify-center">
      <div className="relative">
        <div className="w-24 h-24 bg-golden-yellow rounded-full" />
        <div className="absolute top-0 left-0 w-32 h-1 bg-gray-400 transform rotate-45" />
        <div className="absolute top-0 right-0 w-32 h-1 bg-brilliant-green transform -rotate-45" />
      </div>
    </div>
  },
]

export default function FeatureSections() {
  return (
    <div className="space-y-0">
      {features.map((feature, index) => (
        <section
          key={feature.title}
          className={`py-24 md:py-32 bg-gradient-to-br ${feature.bgGradient}`}
        >
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div
              className={`grid md:grid-cols-2 gap-12 items-center ${
                feature.layout === 'right-text' ? 'md:grid-flow-dense' : ''
              }`}
            >
              {feature.layout === 'left-text' ? (
                <>
                  <motion.div
                    initial={{ opacity: 0, x: -50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    <h2 className="text-4xl md:text-5xl lg:text-[56px] font-bold text-black mb-6">
                      {feature.title}
                    </h2>
                    <p className="text-body-lg text-body-gray leading-relaxed">
                      {feature.description}
                    </p>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, x: 50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    {feature.visual}
                  </motion.div>
                </>
              ) : (
                <>
                  <motion.div
                    initial={{ opacity: 0, x: -50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                    className="md:col-start-2"
                  >
                    {feature.visual}
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, x: 50 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6 }}
                  >
                    <h2 className="text-4xl md:text-5xl lg:text-[56px] font-bold text-black mb-6">
                      {feature.title}
                    </h2>
                    <p className="text-body-lg text-body-gray leading-relaxed">
                      {feature.description}
                    </p>
                  </motion.div>
                </>
              )}
            </div>
          </div>
        </section>
      ))}
    </div>
  )
}


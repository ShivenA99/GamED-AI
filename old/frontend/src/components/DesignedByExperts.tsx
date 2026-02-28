'use client'

import { motion } from 'framer-motion'

const institutions = [
  'Stanford',
  'MIT',
  'Google',
  'Caltech',
  'Harvard',
  'Microsoft',
]

export default function DesignedByExperts() {
  return (
    <section className="py-16 bg-dark-navy">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Designed by experts
          </h2>
          <p className="text-lg text-gray-300 mb-12 max-w-2xl mx-auto">
            All of our courses are crafted by award-winning teachers and professionals from top institutions.
          </p>

          {/* Institution Logos Grid */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-8 max-w-4xl mx-auto">
            {institutions.map((institution, index) => (
              <motion.div
                key={institution}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 0.6, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                whileHover={{ opacity: 1 }}
                className="text-white text-center font-semibold text-sm md:text-base"
              >
                {institution}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}


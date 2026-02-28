'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'

export default function Header() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white/95 backdrop-blur-md shadow-sm'
          : 'bg-white'
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
        <Link href="/" className="text-2xl font-bold text-black hover:opacity-80 transition-opacity">
          GamED.AI
        </Link>
        
        <div className="hidden md:flex items-center gap-8">
          <Link
            href="/courses"
            className="text-body-gray hover:text-black transition-colors relative group"
          >
            Courses
            <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-black group-hover:w-full transition-all duration-300" />
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/signin"
            className="hidden md:block px-6 py-2 rounded-full border border-gray-300 text-black hover:bg-gray-50 transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/app"
            className="px-6 py-3 rounded-full bg-brilliant-green text-white font-medium hover:scale-105 transition-transform shadow-md"
          >
            Get started
          </Link>
        </div>
      </nav>
    </motion.header>
  )
}


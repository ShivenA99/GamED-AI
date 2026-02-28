'use client'

import Link from 'next/link'
import { Facebook, Instagram, Twitter, Linkedin } from 'lucide-react'

const footerLinks = {
  Product: ['Courses', 'Pricing', 'Gift', 'Help'],
  Company: ['About', 'Careers', 'Educators'],
  'Behind Scenes': ['AI Blog', 'Visual Algebra'],
}

export default function Footer() {
  return (
    <footer className="bg-black text-white py-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-4 gap-8 mb-12">
          <div>
            <Link href="/" className="text-2xl font-bold mb-4 block">
              GamED.AI
            </Link>
          </div>
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h3 className="font-semibold mb-4">{category}</h3>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link}>
                    <Link
                      href={`/${link.toLowerCase().replace(' ', '-')}`}
                      className="text-gray-400 hover:text-white transition-colors"
                    >
                      {link}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Social Icons */}
        <div className="flex items-center gap-4 mb-8">
          {[
            { icon: Facebook, href: '#', name: 'Facebook' },
            { icon: Instagram, href: '#', name: 'Instagram' },
            { icon: Twitter, href: '#', name: 'Twitter' },
            { icon: Linkedin, href: '#', name: 'LinkedIn' },
          ].map(({ icon: Icon, href, name }) => (
            <Link
              key={name}
              href={href}
              className="w-8 h-8 text-gray-400 hover:text-white transition-colors"
            >
              <Icon className="w-full h-full" />
            </Link>
          ))}
        </div>

        {/* Copyright */}
        <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-400">
          <p>© 2025 GamED.AI Worldwide, Inc.</p>
          <div className="flex gap-4">
            <Link href="/terms" className="hover:text-white transition-colors">
              Terms
            </Link>
            <Link href="/privacy" className="hover:text-white transition-colors">
              Privacy
            </Link>
            <Link href="/ccpa" className="hover:text-white transition-colors">
              CCPA
            </Link>
          </div>
        </div>
      </div>
    </footer>
  )
}


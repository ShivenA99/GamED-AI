import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'brilliant-green': '#28C66E',
        'vibrant-blue': '#4E72FF',
        'deep-purple': '#8B5CF6',
        'warm-orange': '#FF9F43',
        'golden-yellow': '#FFD700',
        'dark-navy': '#0F1419',
        'light-lavender': '#F5F3FF',
        'mint-green': '#D4F4DD',
        'peach-start': '#FFE4D9',
        'peach-end': '#FFD4C4',
        'body-gray': '#374151',
        'muted-gray': '#6B7280',
      },
      fontFamily: {
        display: ['Charter', 'Georgia', 'serif'],
        body: ['Inter', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'hero': ['72px', { lineHeight: '1.1', fontWeight: '700' }],
        'section': ['48px', { lineHeight: '1.2', fontWeight: '700' }],
        'subsection': ['32px', { lineHeight: '1.3', fontWeight: '600' }],
        'body-lg': ['20px', { lineHeight: '1.6', fontWeight: '400' }],
        'body': ['16px', { lineHeight: '1.7', fontWeight: '400' }],
      },
      screens: {
        'mobile': '320px',
        'tablet': '768px',
        'desktop': '1024px',
        'large': '1440px',
      },
    },
  },
  plugins: [],
}
export default config


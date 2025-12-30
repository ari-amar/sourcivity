/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette based on existing CSS variables
        background: 'hsl(220 20% 98%)',
        foreground: 'hsl(220 10% 20%)',
        surface: 'hsl(0 0% 100%)',
        'surface-foreground': 'hsl(220 10% 15%)',
        sidebar: 'hsl(220 20% 96%)',
        'sidebar-foreground': 'hsl(220 10% 25%)',
        card: 'hsl(0 0% 100%)',
        'card-foreground': 'hsl(220 10% 15%)',
        popup: 'hsl(0 0% 100%)',
        'popup-foreground': 'hsl(220 10% 15%)',
        primary: {
          DEFAULT: 'hsl(217 91% 60%)',
          foreground: 'hsl(0 0% 100%)',
        },
        secondary: {
          DEFAULT: 'hsl(220 15% 95%)',
          foreground: 'hsl(220 10% 30%)',
        },
        muted: {
          DEFAULT: 'hsl(220 15% 96%)',
          foreground: 'hsl(220 10% 45%)',
        },
        accent: {
          DEFAULT: 'hsl(220 15% 94%)',
          foreground: 'hsl(220 10% 25%)',
        },
        destructive: {
          DEFAULT: 'hsl(0 84% 60%)',
          foreground: 'hsl(0 0% 100%)',
        },
        border: 'hsl(220 15% 90%)',
        input: 'hsl(220 15% 90%)',
        ring: 'hsl(217 91% 60%)',
      },
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        caveat: ['Caveat', 'cursive'],
      },
      spacing: {
        '1': '0.25rem',
        '2': '0.5rem',
        '3': '0.75rem',
        '4': '1rem',
        '6': '1.5rem',
        '8': '2rem',
        '12': '3rem',
        '16': '4rem',
      },
      zIndex: {
        'content-low': '10',
        'content': '20',
        'content-high': '30',
        'nav-low': '100',
        'nav': '200',
        'nav-sticky': '300',
        'overlay': '400',
        'spotlight': '1000',
        'critical': '2000',
      },
      keyframes: {
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'bounce-gentle': {
          '0%, 100%': {
            transform: 'translateY(0)',
            animationTimingFunction: 'cubic-bezier(0.8, 0, 1, 1)',
          },
          '50%': {
            transform: 'translateY(-10%)',
            animationTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)',
          },
        },
      },
      animation: {
        'spin-slow': 'spin-slow 8s linear infinite',
        'bounce-gentle': 'bounce-gentle 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
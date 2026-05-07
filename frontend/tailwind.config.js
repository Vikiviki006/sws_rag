/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          700: '#2d2d3d',
          800: '#1e1e2e',
          900: '#181825',
          950: '#11111b',
        },
        signal: {
          400: '#89b4fa',
          600: '#3174f1',
        }
      },
      animation: {
        'fade-up': 'fadeUp 0.3s ease-out forwards',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}

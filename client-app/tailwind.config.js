/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {},
    },
    plugins: [],
    theme: {
        extend: {
          keyframes: {
            fadeIn: { '0%': { opacity: 0, transform: 'scale(0.98)' }, '100%': { opacity: 1, transform: 'scale(1)' } }
          },
          animation: {
            fadeIn: 'fadeIn 0.2s ease-out'
          }
        }
      }
      
      
  }
  
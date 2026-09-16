/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        finance: {
          dark: "#0a0e17",
          card: "#111827",
          border: "#1f293d",
          accent: "#10b981",
          accentHover: "#059669",
          muted: "#94a3b8",
          highlight: "#38bdf8",
          warning: "#f59e0b",
          danger: "#ef4444"
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

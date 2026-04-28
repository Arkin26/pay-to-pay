/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        playto: {
          orange: "#F97316",
          bg0: "#0a0a0a",
          bg1: "#111111",
          bg2: "#1a1a1a",
          border: "#2a2a2a",
          muted: "#9ca3af",
        },
      },
    },
  },
  plugins: [],
};

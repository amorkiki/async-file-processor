/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        wood: {
          bg: "#FAF7F2",
          card: "#FFFCF8",
          border: "#F0DFCF",
          main: "#E8A87C",
          light: "#F2C394",
          muted: "#C9B8A8",
          text: "#6B635C",
          title: "#524940"
        }
      }
    }
  },
  plugins: [],
}

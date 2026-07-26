/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.{html,js}",
    "./core/**/*.{html,js}",
    "./theme/**/*.{html,js}",

    // Si tu as des templates dans des apps
    "./**/templates/**/*.{html,js}",

    // Tes fichiers JS côté static
    "./static/src/**/*.{js,ts}",
    "./static/**/*.{js,ts}",
  ],
  theme: {
    // Doit rester synchronisé avec le bloc @theme de static/src/input.css (v4)
    // et avec la config CDN de templates/core/base.html (mode DEBUG).
    extend: {
      screens: {
        xs: "475px",
      },
      colors: {
        dark: "#08080a",
        card: "#111114",
        border: "#1e1e23",
        muted: "#9ca3af",
        accent: "#e8e0d0",
      },
      fontFamily: {
        display: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
      keyframes: {
        "slide-in": {
          "0%": { opacity: "0", transform: "translateX(1rem)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "fade-out": {
          "0%": { opacity: "1", transform: "translateX(0)" },
          "100%": { opacity: "0", transform: "translateX(1rem)" },
        },
        "fade-down": {
          "0%": { opacity: "0", transform: "translateY(-8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "infinite-scroll": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "slide-in": "slide-in 0.3s ease-out forwards",
        "fade-out": "fade-out 0.4s ease-in forwards",
        "fade-down": "fade-down 0.4s ease-out forwards",
        "infinite-scroll": "infinite-scroll 40s linear infinite",
      },
    },
  },
  plugins: [
    function ({ addUtilities }) {
      addUtilities({
        ".pause": { "animation-play-state": "paused" },
        ".pause-hover:hover": { "animation-play-state": "paused" },
      });
    },
  ],
};

/** Design tokens live as CSS variables in src/index.css (light + dark). */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: v("paper"), panel: v("panel"), ink: v("ink"), muted: v("muted"), grid: v("grid"),
        accent: v("accent"), risk: v("risk"), riskwash: v("riskwash"), peer: v("peer"), calm: v("calm"), focus: v("focus"),
      },
      fontFamily: { sans: ['"Inter"', "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"] },
      borderRadius: { panel: "8px", card: "12px" },
      boxShadow: { card: "0 1px 2px rgb(var(--shadow) / 0.04), 0 2px 8px rgb(var(--shadow) / 0.05)" },
    },
  },
  plugins: [],
};

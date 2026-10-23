/** Design tokens live as CSS variables in src/index.css (light + dark). */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: v("paper"), panel: v("panel"), ink: v("ink"), muted: v("muted"), grid: v("grid"),
        risk: v("risk"), riskwash: v("riskwash"), peer: v("peer"), calm: v("calm"), focus: v("focus"),
      },
      fontFamily: { sans: ['"Public Sans"', "system-ui", "sans-serif"] },
      borderRadius: { panel: "6px" },
    },
  },
  plugins: [],
};

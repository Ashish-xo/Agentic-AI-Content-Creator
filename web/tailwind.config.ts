import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#12161f",
        edge: "#1f2530",
        accent: "#87cade",
        accent2: "#d3b1de",
      },
    },
  },
  plugins: [],
};
export default config;

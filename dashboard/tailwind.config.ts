import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      keyframes: {
        'pulse-yellow': {
          '0%, 100%': { borderColor: 'rgb(234 179 8 / 0.3)', boxShadow: '0 0 0 0 rgb(234 179 8 / 0.3)' },
          '50%': { borderColor: 'rgb(234 179 8 / 0.8)', boxShadow: '0 0 20px 2px rgb(234 179 8 / 0.5)' },
        },
        'pulse-orange': {
          '0%, 100%': { borderColor: 'rgb(249 115 22 / 0.3)', boxShadow: '0 0 0 0 rgb(249 115 22 / 0.3)' },
          '50%': { borderColor: 'rgb(249 115 22 / 0.8)', boxShadow: '0 0 20px 2px rgb(249 115 22 / 0.5)' },
        },
      },
      animation: {
        'pulse-yellow': 'pulse-yellow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-orange': 'pulse-orange 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      scale: {
        '102': '1.02',
      },
    },
  },
  plugins: [],
};
export default config;

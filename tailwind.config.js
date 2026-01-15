/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--color-border) / <alpha-value>)",
        input: "hsl(var(--color-border) / <alpha-value>)",
        ring: "hsl(var(--color-primary) / <alpha-value>)",
        background: "hsl(var(--color-background) / <alpha-value>)",
        foreground: "hsl(var(--color-text-primary) / <alpha-value>)",
        primary: {
          DEFAULT: "hsl(var(--color-primary) / <alpha-value>)",
          foreground: "#ffffff",
          hover: "hsl(var(--color-primary-hover) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "hsl(var(--color-surface-elevated) / <alpha-value>)",
          foreground: "hsl(var(--color-text-primary) / <alpha-value>)",
        },
        destructive: {
          DEFAULT: "hsl(var(--color-danger) / <alpha-value>)",
          foreground: "#ffffff",
        },
        muted: {
          DEFAULT: "hsl(var(--color-surface-elevated) / <alpha-value>)",
          foreground: "hsl(var(--color-text-muted) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--color-accent) / <alpha-value>)",
          foreground: "#ffffff",
        },
        popover: {
          DEFAULT: "hsl(var(--color-surface) / <alpha-value>)",
          foreground: "hsl(var(--color-text-primary) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--color-surface) / <alpha-value>)",
          foreground: "hsl(var(--color-text-primary) / <alpha-value>)",
        },
        // Custom semantic colors
        success: "hsl(var(--color-success) / <alpha-value>)",
        warning: "hsl(var(--color-warning) / <alpha-value>)",
        surface: {
          DEFAULT: "hsl(var(--color-surface) / <alpha-value>)",
          elevated: "hsl(var(--color-surface-elevated) / <alpha-value>)",
        },
        text: {
          primary: "hsl(var(--color-text-primary) / <alpha-value>)",
          secondary: "hsl(var(--color-text-secondary) / <alpha-value>)",
          muted: "hsl(var(--color-text-muted) / <alpha-value>)",
        }
      },
      borderRadius: {
        lg: "0.5rem",
        xl: "0.75rem",
        "2xl": "1rem",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
}


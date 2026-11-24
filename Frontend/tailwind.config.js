/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // PHILOS Design System Colors - Extended for Space Theme
        philos: {
          // Deep Space Backgrounds
          bg: {
            void: "#030712",
            "deep-space": "#080D18",
            primary: "#080D18",
            secondary: "#101827",
            tertiary: "#172235",
            panel: "rgba(16, 24, 39, 0.85)",
            "panel-hover": "rgba(23, 34, 53, 0.9)",
          },
          border: {
            DEFAULT: "#263449",
            hover: "#3A4F6B",
            subtle: "#1E2A3A",
            glow: "rgba(101, 217, 255, 0.3)",
          },
          // Cyan & Icy Blue Highlights
          accent: {
            cyan: "#65D9FF",
            "cyan-hover": "#3BB8E6",
            "cyan-muted": "rgba(101, 217, 255, 0.15)",
            "icy-blue": "#8BE9FD",
            "icy-blue-hover": "#65D9FF",
            // Restrained Violet Accents
            violet: "#A78BFA",
            "violet-hover": "#8B5CF6",
            "violet-muted": "rgba(167, 139, 250, 0.12)",
            "violet-deep": "#7C3AED",
            // Legacy support
            primary: "#65D9FF",
            "primary-hover": "#3BB8E6",
            secondary: "#A78BFA",
            "secondary-hover": "#8B5CF6",
          },
          text: {
            primary: "#F1F5F9",
            secondary: "#94A3B8",
            muted: "#64748B",
            "on-accent": "#030712",
          },
          success: "#22C55E",
          warning: "#F59E0B",
          error: "#EF4444",
          info: "#65D9FF",
          // Atmospheric Glow Colors
          glow: {
            cyan: "rgba(59, 130, 246, 0.18)",
            "cyan-strong": "rgba(59, 130, 246, 0.25)",
            violet: "rgba(124, 58, 237, 0.15)",
            "violet-strong": "rgba(124, 58, 237, 0.22)",
            rose: "rgba(236, 72, 153, 0.12)",
            "rose-strong": "rgba(236, 72, 153, 0.18)",
          },
          // Starfield Colors
          star: {
            white: "#FFFFFF",
            cyan: "#65D9FF",
            icy: "#8BE9FD",
            violet: "#A78BFA",
          },
          // Glass Panel Effects
          glass: {
            bg: "rgba(16, 24, 39, 0.7)",
            "bg-strong": "rgba(16, 24, 39, 0.85)",
            border: "rgba(101, 217, 255, 0.1)",
            "border-hover": "rgba(101, 217, 255, 0.2)",
          },
        },
      },
      spacing: {
        "1": "0.25rem",   /* 4px */
        "2": "0.5rem",    /* 8px */
        "3": "0.75rem",   /* 12px */
        "4": "1rem",      /* 16px */
        "5": "1.25rem",   /* 20px */
        "6": "1.5rem",    /* 24px */
        "8": "2rem",      /* 32px */
        "10": "2.5rem",   /* 40px */
        "12": "3rem",     /* 48px */
        "16": "4rem",     /* 64px */
      },
      borderRadius: {
        sm: "0.25rem",    /* 4px */
        md: "0.375rem",   /* 6px */
        lg: "0.5rem",     /* 8px */
        xl: "0.75rem",    /* 12px */
        "2xl": "1rem",    /* 16px */
        full: "9999px",
      },
      boxShadow: {
        sm: "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        md: "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
        lg: "0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.15)",
        xl: "0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.15)",
        "glow-cyan": "0 0 20px rgba(59, 130, 246, 0.25), 0 0 40px rgba(59, 130, 246, 0.1)",
        "glow-violet": "0 0 20px rgba(124, 58, 237, 0.2), 0 0 40px rgba(124, 58, 237, 0.08)",
        glass: "0 4px 24px rgba(3, 7, 18, 0.4), 0 0 0 1px rgba(101, 217, 255, 0.05)",
        "glass-hover": "0 8px 32px rgba(3, 7, 18, 0.5), 0 0 0 1px rgba(101, 217, 255, 0.12)",
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1.5" }],
        sm: ["0.875rem", { lineHeight: "1.5" }],
        base: ["1rem", { lineHeight: "1.5" }],
        lg: ["1.125rem", { lineHeight: "1.5" }],
        xl: ["1.25rem", { lineHeight: "1.5" }],
        "2xl": ["1.5rem", { lineHeight: "1.25" }],
        "3xl": ["1.875rem", { lineHeight: "1.25" }],
        "4xl": ["2.25rem", { lineHeight: "1.25" }],
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Monaco", "Consolas", "monospace"],
      },
      fontWeight: {
        normal: "400",
        medium: "500",
        semibold: "600",
        bold: "700",
      },
      transitionDuration: {
        fast: "150ms",
        normal: "200ms",
        slow: "300ms",
      },
      transitionTimingFunction: {
        DEFAULT: "ease",
      },
      animation: {
        "twinkle-slow": "twinkle 3000ms ease-in-out infinite",
        "twinkle-normal": "twinkle 2000ms ease-in-out infinite",
        "twinkle-fast": "twinkle 1200ms ease-in-out infinite",
        "drift-slow": "drift 12000ms linear infinite",
        "drift-normal": "drift 8000ms linear infinite",
        "drift-fast": "drift 5000ms linear infinite",
        "pulse-slow": "pulse 4000ms ease-in-out infinite",
        "pulse-normal": "pulse 3000ms ease-in-out infinite",
        "pulse-fast": "pulse 2000ms ease-in-out infinite",
      },
      keyframes: {
        twinkle: {
          "0%, 100%": { opacity: "0.3", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.2)" },
        },
        drift: {
          "0%": { transform: "translate(0, 0)" },
          "100%": { transform: "translate(100px, 100px)" },
        },
        pulse: {
          "0%, 100%": { opacity: "0.1" },
          "50%": { opacity: "0.2" },
        },
      },
      zIndex: {
        dropdown: "100",
        sticky: "200",
        fixed: "300",
        "modal-backdrop": "400",
        modal: "500",
        popover: "600",
        tooltip: "700",
        "space-bg": "0",
        "space-content": "10",
      },
    },
  },
  plugins: [],
};
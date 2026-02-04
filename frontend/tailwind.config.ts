import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Cisco-inspired dark theme
        background: {
          DEFAULT: '#0A0E14',
          elevated: '#1C2433',
          hover: '#252D3D',
        },
        primary: {
          DEFAULT: '#049FD9',
          hover: '#0BB5F5',
          muted: '#049FD9/20',
        },
        success: {
          DEFAULT: '#00D084',
          muted: '#00D084/20',
        },
        warning: {
          DEFAULT: '#FFC043',
          muted: '#FFC043/20',
        },
        error: {
          DEFAULT: '#FF4757',
          muted: '#FF4757/20',
        },
        text: {
          primary: '#E6E8EB',
          secondary: '#8B95A5',
          muted: '#5A6677',
        },
        border: {
          DEFAULT: '#2A3544',
          hover: '#3A4554',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(4, 159, 217, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(4, 159, 217, 0.8)' },
        },
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(4, 159, 217, 0.3)',
        'glow-success': '0 0 20px rgba(0, 208, 132, 0.3)',
        'glow-error': '0 0 20px rgba(255, 71, 87, 0.3)',
      },
    },
  },
  plugins: [],
};

export default config;

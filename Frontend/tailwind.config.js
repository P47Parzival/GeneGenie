/** @type {import('tailwindcss').Config} */
export default {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        bio: '0 0 38px rgba(34, 211, 238, 0.16)',
      },
      backgroundImage: {
        'data-grid':
          'linear-gradient(rgba(34,211,238,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(16,185,129,0.08) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
};

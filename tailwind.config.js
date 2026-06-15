/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html', './**/templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        karams: {
          primary: '#FF9220',
          dark: '#E07A10',
          light: '#FFB366',
          subtle: '#FFF5EB',
          bg: '#FFFFFF',
        },
      },
      fontFamily: {
        display: ['Playfair Display', 'serif'],
        sans: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

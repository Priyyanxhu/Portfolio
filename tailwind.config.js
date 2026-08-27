module.exports = {
  darkMode: 'class',
  content: ['./index.html'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter','system-ui'],
        display: ['Space Grotesk','sans-serif'],
        mono: ['JetBrains Mono','monospace']
      }
    }
  },
  corePlugins: { preflight: true }
}

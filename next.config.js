/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    GROQ_API_KEY: process.env.GROQ_API_KEY,
  },
  // Ensure we're not doing static export (Vercel handles SSR automatically)
  output: undefined,
}

module.exports = nextConfig
import type { NextConfig } from 'next'

// Read when `next build` runs: rewrites are baked into the build output, so the production
// image sets this as a build arg (http://backend:8000, the backend's name on the internal
// compose network). In production Apache routes /api straight to the backend; this rewrite
// is the fallback that keeps /api working through an SSH tunnel to the frontend port.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || 'http://127.0.0.1:8000'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Self-contained server bundle (server.js + only the node_modules it needs) for the
  // production image; `next dev` ignores it.
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_ORIGIN}/:path*`,
      },
    ]
  },
}

export default nextConfig

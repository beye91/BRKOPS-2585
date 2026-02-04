/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,

  // Environment variables available on client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  },

  // Disable x-powered-by header
  poweredByHeader: false,

  // Image optimization
  images: {
    domains: ['localhost'],
    unoptimized: true,
  },

  // Transpile specific packages if needed
  transpilePackages: ['framer-motion'],
};

module.exports = nextConfig;

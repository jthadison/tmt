import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // Configure for Docker deployment
  output: 'standalone',
  // Explicitly define path mappings for Docker build environment
  experimental: {
    externalDir: true,
  },
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Add alias resolution for @ paths
    const baseDir = path.resolve(__dirname)
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': baseDir,
      '@/lib': path.resolve(baseDir, 'lib'),
      '@/components': path.resolve(baseDir, 'components'),
      '@/hooks': path.resolve(baseDir, 'hooks'),
      '@/types': path.resolve(baseDir, 'types'),
    }

    // Ensure proper module resolution
    config.resolve.extensions = ['.ts', '.tsx', '.js', '.jsx', '.json', ...config.resolve.extensions]

    return config
  },
};

export default nextConfig;

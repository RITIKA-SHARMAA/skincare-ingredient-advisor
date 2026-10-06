import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  // Produces a small self-contained server for the Cloud Run image.
  output: 'standalone',
};

export default config;

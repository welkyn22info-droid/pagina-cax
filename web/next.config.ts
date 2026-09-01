import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Nginx enruta /api/* a FastAPI (proxy/nginx.conf); en dev, sin proxy,
  // NEXT_PUBLIC_API_BASE apunta directo a http://localhost:8000.
  reactStrictMode: true,
};

export default nextConfig;

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["http://localhost:3000", "http://127.0.0.1:3000", "http://172.168.100.221:3000"],
};

export default nextConfig;

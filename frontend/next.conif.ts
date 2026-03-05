import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "http://172.168.100.221:3000",
    "http://localhost:3000"
  ]
};

export default nextConfig;

import type { NextConfig } from "next";

const allowedDevOrigins = (
  process.env.FRONTEND_ALLOWED_DEV_ORIGINS ??
  "http://localhost:3000,http://127.0.0.1:3000"
)
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins,
};

export default nextConfig;

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [
          {
            type: "host",
            value: "24econews.vercel.app",
          },
        ],
        destination: "https://www.24econews.com/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;

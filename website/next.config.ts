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
        destination: "https://24econews.com/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;

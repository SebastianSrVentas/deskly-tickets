import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Genera un servidor autonomo y minimo para la imagen de produccion.
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;

// Exports plain static files to out/, so the site can go on Vercel, Netlify, GitHub Pages or any web server.
// For a site served from a subfolder (GitHub Pages), set NEXT_PUBLIC_BASE_PATH=/repo-name when building.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export default {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath,
  turbopack: { root: import.meta.dirname },
};

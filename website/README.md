# Chamber website

The public product site. It's a Next.js app that exports plain static files, so it needs no server.

## Run it locally

```bash
npm install
npm run dev        # http://localhost:3100
```

## Build

```bash
npm run build      # writes the site to out/
npm run start      # previews out/ at http://localhost:3100
```

## Deploy

- **Vercel:** import the repository and set the Root Directory to `website`.
- **Netlify or Cloudflare Pages:** set the base directory to `website`, the build command to `npm run build`, and the output directory to `out`.
- **GitHub Pages:** build with `NEXT_PUBLIC_BASE_PATH=/chamber npm run build` and publish `out/`.
- **Any web server:** upload the contents of `out/`.

All numbers on the site come from the project's own runs, listed in the main `README.md`. The demos are simulations that run in the visitor's browser, and nothing typed into them is sent anywhere.

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/postcss';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

// MIT/ISC require the copyright and permission notice to ship with the code: collect the
// licence text of every bundled npm package into THIRD_PARTY_LICENSES.txt next to the JS.
function thirdPartyLicenses() {
  return {
    name: 'third-party-licenses',
    generateBundle(_: unknown, bundle: Record<string, any>) {
      const roots = new Set<string>();
      for (const f of Object.values(bundle)) {
        if (f.type !== 'chunk') continue;
        for (const id of Object.keys(f.modules)) {
          const m = id.match(/^(.*\/node_modules\/(?:@[^/]+\/)?[^/]+)\//);
          if (m) roots.add(m[1]);
        }
      }
      const parts = [...roots].sort().map(dir => {
        const pkg = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'));
        const file = readdirSync(dir).find(n => /^licen[cs]e/i.test(n));
        const text = file ? readFileSync(join(dir, file), 'utf8').trim() : `License: ${pkg.license}`;
        return `${pkg.name}@${pkg.version} (${pkg.license})\n\n${text}`;
      });
      (this as any).emitFile({ type: 'asset', fileName: 'THIRD_PARTY_LICENSES.txt', source: parts.join('\n\n' + '-'.repeat(72) + '\n\n') + '\n' });
    },
  };
}

export default defineConfig({
  publicDir: false,
  // Relative base: the lazy graph chunk's CSS is preloaded next to app.js (/assets/dist/), not from the site root.
  base: './',
  plugins: [react(), thirdPartyLicenses()],
  css: {
    postcss: {
      plugins: [tailwindcss()],
    },
  },
  build: {
    outDir: 'static/assets/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        app: 'src/main.tsx',
        styles: 'src/index.css'
      },
      output: {
        entryFileNames: `[name].js`,
        postBanner: (c: any) => (c.fileName.endsWith('.js') ? '/*! Third-party licences: THIRD_PARTY_LICENSES.txt */' : ''),
        // The pages load app.js?v=<build time>. A lazy chunk importing "./app.js" would get a
        // second copy of React, so the code both share lives in a content-hashed core chunk.
        chunkFileNames: `[name]-[hash].js`,
        codeSplitting: { groups: [{ name: 'core', test: /node_modules\/(react|react-dom|scheduler|lucide-react)\/|\/src\/atlas\.ts/ }] },
        assetFileNames: (a: any) => (/GraphView/.test(a.names?.[0] || a.name || '') ? `[name]-[hash].[ext]` : `[name].[ext]`)
      }
    }
  }
});

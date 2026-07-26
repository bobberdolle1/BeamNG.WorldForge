import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Default to localhost so `npm run dev` works outside Docker. The previous
  // default was `http://backend:8000`, a hostname that only resolves inside the
  // compose network, so a plain local dev server proxied to nowhere.
  const apiTarget = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          ws: true,
        },
      },
    },
    build: {
      // Emitting one ~900 kB chunk means any change to app code invalidates the
      // entire download. Splitting the heavy, rarely-changing libraries into
      // their own chunks lets browsers keep them cached across deploys.
      rollupOptions: {
        output: {
          // Function form rather than the object form on purpose. The object
          // form also captures Vite's own runtime helpers (notably the dynamic
          // import preloader) into whichever vendor chunk it lists first, which
          // made the entry chunk statically import the three.js chunk - undoing
          // the lazy load of the 3D viewer. Matching on module path keeps
          // helpers in the entry chunk where they belong.
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return undefined
            }
            if (/node_modules\/(three|@react-three)\//.test(id)) {
              return 'three'
            }
            if (/node_modules\/(leaflet|react-leaflet|@react-leaflet)\//.test(id)) {
              return 'leaflet'
            }
            if (/node_modules\/(i18next|react-i18next)/.test(id)) {
              return 'i18n'
            }
            if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) {
              return 'react'
            }
            return undefined
          },
        },
      },
      chunkSizeWarningLimit: 700,
    },
  }
})

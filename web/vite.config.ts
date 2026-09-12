import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Vestibulinho — Provas Simuladas',
        short_name: 'Vestibulinho',
        description:
          'Provas simuladas com questões reais do Vestibulinho ETEC, de 2008 a 2022.',
        lang: 'pt-BR',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        theme_color: '#1f5fd0',
        background_color: '#f7f7f8',
        icons: [
          { src: 'icone-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icone-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'icone-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Pré-cacheia a casca do app e o banco de questões, mas NÃO as ~220
        // imagens (24 MB): estourar a cota é o jeito mais rápido de o iOS
        // descartar o cache inteiro. As figuras entram sob demanda, abaixo.
        globPatterns: [
          '**/*.{js,css,html}',
          'dados/banco.json',
          'icone-*.png',
          'favicon.png',
        ],
        globIgnores: ['**/dados/imagens/**'],
        // banco.json passa de 500 KB, acima do limite padrão do Workbox
        maximumFileSizeToCacheInBytes: 2 * 1024 * 1024,
        navigateFallback: 'index.html',
        runtimeCaching: [
          {
            // figura nunca muda depois de publicada: CacheFirst é o certo
            urlPattern: ({ url }) => url.pathname.includes('/dados/imagens/'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'figuras-questoes',
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 180 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
})

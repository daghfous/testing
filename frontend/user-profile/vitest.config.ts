import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { defineConfig as vitedefineConfig } from 'vite'
import { configDefaults, defineConfig, mergeConfig } from 'vitest/config'

export default mergeConfig(
  vitedefineConfig({
    plugins: [vue()]
  }),
  defineConfig({
    test: {
      environment: 'jsdom',
      exclude: [...configDefaults.exclude, 'tests/vitest/__mocks__/**', 'tests/vitest/coverageVitest/**'],
      include: ['tests/vitest/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),

      reporters: ['default', 'html'],
      outputFile: {
        html: './tests/vitest/coverageVitest/report.html'
      },
      coverage: {
        provider: 'v8',
        reporter: ['html'],
        reportsDirectory: './tests/vitest/coverageVitest',
        enabled: true,
        include: [
          // accept all
          'src/**/*.{js,ts}',
          // accept constantes files
          '!**/constants/**',
          '!src/**/*constants*.{js,ts}',
          // accept interfaces files
          '!**/interfaces/**',
          // accept lang files
          '!**/lang/**',
          // accept router files
          '!**/router/**'
          // cannot be tested
        ],
        thresholds: {
          statements: 0,
          branches: 40,
          functions: 25,
          lines: 0
        }
      }
    }
  })
)

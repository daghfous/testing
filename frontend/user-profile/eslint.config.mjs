import eslintConfigAteme from '@ateme/eslint-config-ateme/eslint.config.mjs'
import { defineConfig, globalIgnores  } from 'eslint/config'

export default defineConfig([
  globalIgnores([
    'build/*.js',
    'dist/*',
    'node_modules/*',
    'static-up/*',
    '.eslintrc.js',
    'tests/vitest/coverageVitest/*'
  ]),
  eslintConfigAteme
])

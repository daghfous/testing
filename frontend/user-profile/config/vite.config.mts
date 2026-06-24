import { baseConfVite } from '@ateme/ui-devtools/vite/vite.config.js'
import path from 'path'
import {
  defineConfig,
  UserConfig,
  Alias,
  normalizePath
} from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteStaticCopy, ViteStaticCopyOptions } from 'vite-plugin-static-copy'
import svgLoader from 'vite-svg-loader'
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js'

const targetURL = 'http://172.29.71.110/<release-name>'

const server: ServerOptions = {
  open: false,
  proxy: {
    '/users': {
      target: `${targetURL}/users`,
      changeOrigin: true,
      secure: false,
      ws: true,
      rewrite: (path) => path.replace(/^\/users/, ''),
    }
  }
};
/**
 * Array of folder to copy into assets
 */
const viteStaticCopyPlugin: ViteStaticCopyOptions = {
  targets: [
    {
      src: normalizePath(path.resolve(__dirname, '../node_modules/@ateme/cathodic-ui/assets-cathodic-ui/')),
      dest: './'
    },
    {
      src: normalizePath(path.resolve(__dirname, '../node_modules/@ateme/cathodic-ui/static-cathodic-ui/')),
      dest: './'
    }
  ]
}

/**
 * List of product alias
 */
const alias: Alias[] = [
  {
    find: 'src',
    replacement: path.resolve(__dirname, '../src')
  }
]



// https://vitejs.dev/config/
export default defineConfig((userConfig: UserConfig): UserConfig => {
  const plugins = [
    vue({
      features: {
        customElement: true
      }
    }),
    svgLoader(),
    cssInjectedByJsPlugin()
  ]
  const build = {
    manifest: 'manifest.json',
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue']
        }
      }
    }
  }
  const baseConfViteValue: UserConfig = baseConfVite(userConfig, true)

  if (!baseConfViteValue.resolve) baseConfViteValue.resolve = {}
  baseConfViteValue.resolve.alias = alias

  if (!baseConfViteValue.server) baseConfViteValue.server = {}
  baseConfViteValue.server = server

  baseConfViteValue.plugins = plugins
  baseConfViteValue.build = build
  baseConfViteValue.plugins?.push(viteStaticCopy(viteStaticCopyPlugin))
  return baseConfViteValue
})

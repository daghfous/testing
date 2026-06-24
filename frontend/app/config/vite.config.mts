import { baseConfVite } from '@ateme/ui-devtools/vite/vite.config.js'
import path from 'path'
import { defineConfig, normalizePath, ServerOptions, UserConfig } from 'vite'
import { viteStaticCopy, ViteStaticCopyOptions } from 'vite-plugin-static-copy'

const targetURL = 'http://172.29.71.107/<release-name>/users'
const token = 'Bearer xxxx' // Used in case of npm run dev on a PMF
const configure = (proxy) => {
  proxy.on('proxyReq', proxyReq => {
    proxyReq.setHeader('Authorization', token)
  })
}

const server: ServerOptions = {
  host: '127.0.0.1',
  port: 9000,
  open: false,
  fs: {
    // Allow serving files from one level up to the project root
    allow: ['..']
  },
  proxy: {
    '/users': {
      target: `${targetURL}`,
      changeOrigin: true,
      rewrite: path => path.replace(/^\/users\//, ''),
      configure: configure
    },
    '/user-management': {
      target: `${targetURL}`,
      changeOrigin: true,
      rewrite: path => path.replace(/^\/user-management\//, ''),
      configure: configure
    },
    '/alarm-server': {
      target: `${targetURL}`,
      changeOrigin: true,
      rewrite: path => path.replace(/^\/alarm-server\//, ''),
      configure: configure
    },
    '/failover': {
      target: `${targetURL}`,
      changeOrigin: true,
      rewrite: path => path.replace(/^\/failover\//, ''),
      configure: configure
    }
  }
}

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
    },
    {
      src: normalizePath(path.resolve(__dirname, '../static-um/')),
      dest: './'
    }
  ]
}

// https://vitejs.dev/config/
export default defineConfig((userConfig: UserConfig): UserConfig => {
  const baseConfViteValue: UserConfig = baseConfVite(userConfig, true)
  baseConfViteValue.plugins?.push(viteStaticCopy(viteStaticCopyPlugin))
  if (!baseConfViteValue.server) baseConfViteValue.server = {}
  baseConfViteValue.server = server
  baseConfViteValue.optimizeDeps.include = ['moment-timezone']
  baseConfViteValue.resolve.alias = {
    '@': path.resolve(__dirname, '../src'),
    '@store': path.resolve(__dirname, '../src/store'),
    '@interfaces': path.resolve(__dirname, '../src/interfaces')
  }
  return baseConfViteValue
})

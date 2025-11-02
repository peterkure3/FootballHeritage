import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import viteCompression from "vite-plugin-compression";

/**
 * Vite Configuration with Performance Optimizations
 * 
 * Features:
 * - Gzip and Brotli compression for smaller bundle sizes
 * - Code splitting for better caching and faster loads
 * - Tree shaking to remove unused code
 * - Minification for production builds
 * - Source maps for debugging
 */
export default defineConfig({
  plugins: [
    // React with SWC for faster builds
    react(),
    
    // Tailwind CSS v4
    tailwindcss(),
    
    // Gzip compression (widely supported)
    viteCompression({
      verbose: true, // Log compression results
      disable: false, // Enable in production
      threshold: 10240, // Only compress files > 10KB
      algorithm: 'gzip', // Use gzip compression
      ext: '.gz', // File extension for compressed files
      deleteOriginFile: false, // Keep original files
    }),
    
    // Brotli compression (better compression, modern browsers)
    viteCompression({
      verbose: true,
      disable: false,
      threshold: 10240,
      algorithm: 'brotliCompress', // Brotli compression
      ext: '.br',
      deleteOriginFile: false,
    }),
  ],
  
  // Build optimizations
  build: {
    // Target modern browsers for smaller bundles
    target: 'es2015',
    
    // Enable minification
    minify: 'esbuild',
    
    // Generate source maps for debugging (disable in production if needed)
    sourcemap: true,
    
    // Chunk size warnings
    chunkSizeWarningLimit: 1000, // KB
    
    // Manual chunk splitting for better caching
    rollupOptions: {
      output: {
        // Split vendor code into separate chunk
        manualChunks: {
          // React and React DOM in one chunk
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          
          // State management and data fetching
          'state-vendor': ['zustand', '@tanstack/react-query'],
          
          // UI libraries
          'ui-vendor': ['lucide-react', 'react-hot-toast'],
        },
        
        // Naming pattern for chunks
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
      },
    },
    
    // CSS code splitting
    cssCodeSplit: true,
    
    // Optimize dependencies
    commonjsOptions: {
      transformMixedEsModules: true,
    },
  },
  
  // Development server configuration
  server: {
    port: 5173,
    strictPort: false, // Try next port if 5173 is busy
    open: false, // Don't auto-open browser
    cors: true, // Enable CORS for API calls
  },
  
  // Preview server (for testing production build)
  preview: {
    port: 4173,
    strictPort: false,
  },
  
  // Dependency optimization
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'zustand',
      '@tanstack/react-query',
      'lucide-react',
      'react-hot-toast',
    ],
  },
});

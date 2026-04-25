import { motion } from "framer-motion";

export default function Layout({ children }) {
  return (
    <div className="relative min-h-screen overflow-x-hidden selection:bg-emerald-100 selection:text-emerald-900">
      {/* Organic Jungle Blobs */}
      <motion.div 
        animate={{ 
          scale: [1, 1.1, 1],
          rotate: [0, 10, 0],
          x: [0, 20, 0]
        }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        className="jungle-blob blob-1" 
      />
      <motion.div 
        animate={{ 
          scale: [1, 1.2, 1],
          rotate: [0, -15, 0],
          x: [0, -30, 0]
        }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
        className="jungle-blob blob-2" 
      />
      
      <div className="relative z-10">
        {children}
      </div>

      {/* Structured Grid Overlay (Subtle) */}
      <div className="pointer-events-none fixed inset-0 z-0 opacity-[0.015]" 
           style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 0)', backgroundSize: '40px 40px' }} 
      />
    </div>
  );
}

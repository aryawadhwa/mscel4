import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

const WORDS = [
  "income", "credit", "debt", "age", "gender", "race", "zip", "approval",
  "bias", "fairness", "synthetic", "data", "schema", "model", "audit"
];

export default function JumbledHero() {
  const [isStructured, setIsStructured] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsStructured(true), 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="relative flex h-[300px] w-full flex-col items-center justify-center overflow-hidden py-20">
      <div className="relative h-full w-full max-w-lg">
        {WORDS.map((word, i) => (
          <motion.span
            key={i}
            layout
            initial={{ 
              x: Math.random() * 400 - 200, 
              y: Math.random() * 200 - 100, 
              rotate: Math.random() * 90 - 45,
              opacity: 0 
            }}
            animate={isStructured ? {
              x: (i % 5) * 80 - 160,
              y: Math.floor(i / 5) * 40 - 40,
              rotate: 0,
              opacity: 0.15,
              scale: 0.9,
            } : {
              opacity: 0.4,
              scale: 1,
            }}
            transition={{ 
              type: "spring", 
              stiffness: 50, 
              damping: 20,
              delay: i * 0.02 
            }}
            className="absolute cursor-default text-sm font-bold uppercase tracking-widest text-emerald-900"
          >
            {word}
          </motion.span>
        ))}
        
        <AnimatePresence>
          {isStructured && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 1, ease: [0.16, 1, 0.3, 1], delay: 0.5 }}
              className="relative z-10 text-center"
            >
              <h1 className="font-display text-5xl font-bold tracking-tight text-gray-900 sm:text-7xl">
                de.bias
              </h1>
              <p className="mt-4 text-lg font-medium text-emerald-800/60">
                Structure from entropy. Fairness from data.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

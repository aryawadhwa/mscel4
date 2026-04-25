import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

export default function CurvedTextHero() {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"]
  });

  const pathLength = useTransform(scrollYProgress, [0, 1], [0, 1]);
  const textOffset = useTransform(scrollYProgress, [0, 1], ["100%", "0%"]);

  return (
    <div ref={containerRef} className="relative flex h-[500px] w-full flex-col items-center justify-center overflow-hidden py-32 selection:bg-black selection:text-white">
      <svg className="absolute inset-0 h-full w-full pointer-events-none overflow-visible" viewBox="0 0 1000 500">
        <defs>
          <path
            id="curvePath"
            d="M -100 400 Q 150 450 300 300 C 450 150 550 150 700 300 Q 850 450 1100 400"
            fill="transparent"
          />
        </defs>
        
        <motion.path
          d="M -100 400 Q 150 450 300 300 C 450 150 550 150 700 300 Q 850 450 1100 400"
          fill="transparent"
          stroke="rgba(0,0,0,0.03)"
          strokeWidth="1"
          style={{ pathLength }}
        />

        <text className="font-serif italic text-4xl fill-black/20">
          <textPath href="#curvePath" startOffset="0%">
            Entropy is the natural state of data. Structure is the intervention.
          </textPath>
        </text>

        <motion.text className="font-serif text-5xl fill-black">
          <textPath href="#curvePath" style={{ startOffset: textOffset }}>
            de.bias: Building structural integrity in synthetic credit systems.
          </textPath>
        </motion.text>
      </svg>

      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 text-center max-w-2xl px-6"
      >
        <h1 className="font-serif text-7xl font-medium tracking-tight text-black sm:text-9xl">
          de.bias
        </h1>
        <p className="mt-8 text-xl font-serif italic text-gray-500 leading-relaxed">
          Inspired by the logic of Pretext. <br />
          Formalizing fairness through high-fidelity synthetic data.
        </p>
      </motion.div>
    </div>
  );
}

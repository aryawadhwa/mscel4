import { motion } from "framer-motion";

export const FADE_UP = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] }
};

export const STAGGER_CONTAINER = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export function MotionWrapper({ children, variants = FADE_UP, className = "" }) {
  return (
    <motion.div
      variants={variants}
      initial="initial"
      animate="animate"
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerWrapper({ children, className = "" }) {
  return (
    <motion.div
      variants={STAGGER_CONTAINER}
      initial="initial"
      animate="animate"
      className={className}
    >
      {children}
    </motion.div>
  );
}

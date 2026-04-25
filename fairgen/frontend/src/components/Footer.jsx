import React from 'react';
import { motion } from 'framer-motion';

const FOOTER_NAV = [
  {
    heading: "Platform",
    links: [
      "AI Assistant",
      "Mock Data",
      "Simulated Data",
      "Privacy and Security",
      "System Status",
    ],
  },
  {
    heading: "Synthetic Data",
    links: [
      "Synthetic Data Basics",
      "Data Anonymization",
      "FAQ",
      "The Synthetic Data Dictionary",
      "Synthetic Data SDK",
    ],
  },
  {
    heading: "Use Cases",
    links: [
      "Agentic Data Science",
      "Data Sharing",
      "AI/ML Development",
      "Testing & QA",
    ],
  },
  {
    heading: "Company",
    links: [
      "About Us",
      "Careers",
      "Handbook",
      "Privacy Policy",
      "Terms of Service",
      "Imprint",
    ],
  },
];

export default function Footer({ onLoadDemo, onLogin }) {
  return (
    <footer className="mx-3 sm:mx-6 mb-6 mt-24 sm:mt-32 overflow-hidden rounded-[2.5rem] sm:rounded-[4rem] bg-slate-900 px-6 sm:px-12 pb-10 sm:pb-12 pt-14 sm:pt-20 text-white selection:bg-white selection:text-slate-900">
      <div className="mx-auto max-w-7xl">

        {/* Nav grid */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
          {FOOTER_NAV.map(({ heading, links }) => (
            <div key={heading} className="space-y-3">
              <p className="text-[11px] font-bold uppercase tracking-widest text-white/40">
                {heading}
              </p>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link}>
                    <button className="text-sm font-medium text-white/60 hover:text-white transition-colors text-left">
                      {link}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Wordmark */}
        <div className="mt-20 sm:mt-32">
          <motion.h2
            initial={{ y: 100, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
            className="text-[clamp(3.5rem,18vw,22rem)] font-bold leading-[0.85] tracking-tighter text-white"
          >
            de.bias
          </motion.h2>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 sm:mt-12 flex flex-col items-start justify-between gap-4 border-t border-white/10 pt-8 sm:flex-row sm:items-center">
          <p className="text-xs font-bold text-white/40">
            &copy; 2026 de.bias. High-performance structural calibration.
          </p>
        </div>
      </div>
    </footer>
  );
}

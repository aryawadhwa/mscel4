import { Menu, User } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

export default function Header({ 
  score, 
  scoreTone, 
  result, 
  loading, 
  step, 
  user,
  statusProgress,
  onShowHelp, 
  onLoadDemo, 
  onEditSchema,
  onSetActiveTab,
  onLogin
}) {
  const isConfig = step === "config";
  const [isVisible, setIsVisible] = useState(true);
  const [showMenu, setShowMenu] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsVisible(window.scrollY < 20);
      if (window.scrollY > 20) setShowMenu(false);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.header 
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="fixed top-8 left-0 right-0 z-50 flex justify-center px-6 pointer-events-none"
        >
          <div className="flex w-full max-w-7xl items-center justify-between pointer-events-auto">
            {/* Logo */}
            <button 
              onClick={onEditSchema}
              className="flex items-center transition-transform active:scale-95"
            >
              <span className="text-xl font-bold tracking-tighter text-slate-900">
                de.bias
              </span>
            </button>

            {/* Central Pill Navbar */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center rounded-full bg-white/95 backdrop-blur-md p-1.5 shadow-xl border border-slate-200/60">
              <div className="relative flex items-center gap-1 sm:gap-4 px-3 sm:px-5 py-1.5">
                <button 
                  onClick={() => setShowMenu(!showMenu)}
                  className={`flex items-center gap-2 text-sm font-semibold transition ${showMenu ? 'text-slate-900' : 'text-slate-500 hover:text-slate-900'}`}
                >
                  <Menu size={16} />
                  <span className="hidden sm:inline">Menu</span>
                </button>

                <AnimatePresence>
                  {showMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute left-0 top-[calc(100%+12px)] w-48 overflow-hidden rounded-2xl bg-white/95 p-2 shadow-[0_8px_32px_rgba(0,100,100,0.22)] backdrop-blur-xl"
                    >
                      <button onClick={() => { onEditSchema(); setShowMenu(false); }} className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition">
                        Home
                      </button>
                      <button onClick={() => { onLoadDemo(); setShowMenu(false); }} className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition">
                        Load Demo
                      </button>
                      <a href="https://github.com/aarush-luthra/fairgen" target="_blank" rel="noreferrer" className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition">
                        GitHub
                      </a>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="h-3 w-px bg-slate-200 mx-1" />

                <div className="flex items-center justify-center rounded-full bg-slate-900 px-3 py-1.5 min-w-[45px]">
                  <span className="text-[10px] font-bold tabular-nums text-white">
                    {loading ? `${statusProgress}%` : isConfig ? "100%" : "0%"}
                  </span>
                </div>
              </div>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-4">
              <button 
                onClick={onLogin}
                className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-white shadow-sm border border-slate-100 hover:bg-slate-50 transition active:scale-90"
              >
                {user ? (
                  <img src={user.picture} alt={user.name} className="h-full w-full object-cover" />
                ) : (
                  <User size={18} className="text-slate-400" />
                )}
              </button>
              
              <button 
                onClick={isConfig ? onEditSchema : onLoadDemo}
              className="hidden sm:flex rounded-full bg-white border border-slate-200 px-4 sm:px-6 py-2.5 text-sm font-bold text-slate-900 shadow-sm hover:bg-slate-50 transition active:scale-95"
              >
                {isConfig ? "Edit Schema" : "Load Demo"}
              </button>
            </div>
          </div>
        </motion.header>
      )}
    </AnimatePresence>
  );
}

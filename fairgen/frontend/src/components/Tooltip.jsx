import { Info } from "lucide-react";

export default function Tooltip({ text }) {
  return (
    <span className="group relative inline-flex">
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-300/60 bg-white/50 text-slate-400">
        <Info size={12} />
      </span>
      <span className="pointer-events-none absolute left-1/2 top-7 z-20 hidden w-64 -translate-x-1/2 rounded-xl border border-slate-200/60 bg-white/90 backdrop-blur-md px-3 py-2 text-xs leading-5 text-slate-600 shadow-lg shadow-slate-900/10 group-hover:block">
        {text}
      </span>
    </span>
  );
}

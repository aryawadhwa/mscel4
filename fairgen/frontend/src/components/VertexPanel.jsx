import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// ─── Google Cloud wordmark SVG (inline, no external deps) ────────────────────
function GoogleCloudBadge() {
  return (
    <div className="flex items-center gap-1.5">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="#4285F4"/>
        <path d="M12 4.5C7.86 4.5 4.5 7.86 4.5 12S7.86 19.5 12 19.5 19.5 16.14 19.5 12 16.14 4.5 12 4.5z" fill="white"/>
        <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5z" fill="#4285F4"/>
      </svg>
      <span className="text-[10px] font-semibold text-slate-500 tracking-wide">Powered by Google Cloud</span>
    </div>
  );
}

// ─── DIR badge ────────────────────────────────────────────────────────────────
function DirBadge({ dir, label }) {
  const isGood = dir >= 0.8;
  const isMod = dir >= 0.6;
  const color = isGood
    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : isMod
    ? "text-amber-700 bg-amber-50 border-amber-200"
    : "text-rose-700 bg-rose-50 border-rose-200";
  const legality = dir >= 0.8 ? "Compliant" : dir >= 0.6 ? "Borderline" : "Actionable";

  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <p className="text-[10px] font-bold uppercase tracking-[0.25em] opacity-70">{label}</p>
      <p className="mt-1.5 text-4xl font-bold">{dir.toFixed(3)}</p>
      <p className="mt-1 text-xs font-semibold">Disparate Impact Ratio</p>
      <p className="mt-2 text-xs opacity-80">
        {legality} — {dir >= 0.8 ? ">= 0.8 EEOC threshold" : dir >= 0.6 ? "approaching legal limit" : "below 0.8 EEOC threshold"}
      </p>
    </div>
  );
}

// ─── Approval-by-group mini table ────────────────────────────────────────────
function ApprovalTable({ approvalByGroup }) {
  const entries = Object.entries(approvalByGroup || {});
  if (!entries.length) return null;
  return (
    <div className="mt-3 space-y-3">
      {entries.map(([colName, groups]) => (
        <div key={colName}>
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">{colName}</p>
          <div className="space-y-1.5">
            {Object.entries(groups).map(([group, rate]) => (
              <div key={group} className="flex items-center gap-3">
                <span className="w-24 shrink-0 truncate text-xs font-medium text-slate-600">{group}</span>
                <div className="relative flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-blue-500 to-indigo-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${(rate * 100).toFixed(1)}%` }}
                    transition={{ duration: 0.7, ease: "easeOut" }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-xs font-semibold text-slate-700">
                  {(rate * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main VertexPanel ─────────────────────────────────────────────────────────
export default function VertexPanel({ result, schema }) {
  const [evalResult, setEvalResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canEval = result?.dataset?.length > 0 && result?.beforeDataset?.length > 0;

  async function handleEvaluate() {
    if (!canEval) return;
    setLoading(true);
    setError("");
    setEvalResult(null);
    try {
      const resp = await fetch(`${API_BASE}/model/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset: result.dataset,
          beforeDataset: result.beforeDataset,
          schema: schema,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Evaluation failed");
      if (data.status === "error") throw new Error(data.message || "Evaluation error");
      setEvalResult(data);
    } catch (err) {
      setError(err.message || "Model evaluation failed");
    } finally {
      setLoading(false);
    }
  }

  const dirDelta = evalResult
    ? evalResult.after.DIR - evalResult.before.DIR
    : null;

  return (
    <div className="rounded-2xl bg-gradient-to-br from-white/70 to-blue-50/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(66,133,244,0.15)]">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-blue-500">
            Model-Level Fairness
          </p>
          <h3 className="mt-1 text-lg font-bold text-slate-900">Train &amp; Evaluate</h3>
          <p className="mt-1 text-xs text-slate-500 max-w-xs leading-5">
            Trains a classifier on both datasets and measures whether the model
            itself perpetuates bias — even without using protected attributes.
          </p>
        </div>
        <GoogleCloudBadge />
      </div>

      {/* CTA button */}
      {!evalResult && (
        <button
          id="vertex-train-btn"
          onClick={handleEvaluate}
          disabled={loading || !canEval}
          className={`w-full rounded-xl py-3.5 text-sm font-bold tracking-wide transition active:scale-95
            ${canEval && !loading
              ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-600/25 hover:shadow-blue-600/40"
              : "bg-slate-100 text-slate-400 cursor-not-allowed"
            }`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Training model...
            </span>
          ) : canEval ? (
            "Train Model & Evaluate Fairness"
          ) : (
            "Generate a dataset first"
          )}
        </button>
      )}

      {/* Error */}
      {error && (
        <p className="mt-3 rounded-lg bg-rose-50 border border-rose-200 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </p>
      )}

      {/* Results */}
      <AnimatePresence>
        {evalResult && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-5"
          >
            {/* DIR comparison */}
            <div className="grid grid-cols-2 gap-3">
              <DirBadge dir={evalResult.before.DIR} label="Before Mitigation" />
              <DirBadge dir={evalResult.after.DIR} label="After Mitigation" />
            </div>

            {/* Delta callout */}
            <div
              className={`rounded-xl p-4 text-sm font-medium leading-6
                ${dirDelta > 0
                  ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
                  : "bg-amber-50 border border-amber-200 text-amber-800"
                }`}
            >
              <span className="font-bold">
                {dirDelta > 0 ? `+${dirDelta.toFixed(3)}` : dirDelta?.toFixed(3)} DIR
              </span>{" "}
              — {evalResult.improvement.narrative}
            </div>

            {/* Approval by group */}
            <div className="grid grid-cols-2 gap-5">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-400 mb-2">
                  Before — Model Predictions
                </p>
                <ApprovalTable approvalByGroup={evalResult.before.approvalByGroup} />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-400 mb-2">
                  After — Model Predictions
                </p>
                <ApprovalTable approvalByGroup={evalResult.after.approvalByGroup} />
              </div>
            </div>

            {/* Re-evaluate */}
            <button
              onClick={() => { setEvalResult(null); setError(""); }}
              className="text-xs font-medium text-slate-400 hover:text-slate-600 transition"
            >
              Re-evaluate
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

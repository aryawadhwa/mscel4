import { useState } from "react";
import { useGoogleLogin } from "@react-oauth/google";

import { exportToHuggingFace, exportToGoogleSheets } from "../api/export";

function downloadFile(name, contents, type) {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function DownloadPanel({ config, result }) {
  const [hfToken, setHfToken] = useState("");
  const [repoName, setRepoName] = useState("");
  const [shareState, setShareState] = useState("");
  const [exportState, setExportState] = useState("");
  const [googleExportState, setGoogleExportState] = useState("");
  const dataset = result?.dataset || [];

  function handleCsv() {
    if (!dataset.length) {
      return;
    }
    const headers = Object.keys(dataset[0]);
    const rows = dataset.map((row) => headers.map((header) => JSON.stringify(row[header] ?? "")).join(","));
    downloadFile("de.bias_dataset.csv", [headers.join(","), ...rows].join("\n"), "text/csv");
  }

  function handleJson() {
    if (!result) {
      return;
    }
    downloadFile("de.bias_report.json", JSON.stringify(result, null, 2), "application/json");
  }

  function handleShare() {
    const encoded = btoa(JSON.stringify(config));
    navigator.clipboard.writeText(encoded);
    setShareState("Config copied to clipboard");
    window.setTimeout(() => setShareState(""), 2000);
  }

  async function handleExport() {
    if (!dataset.length || !hfToken || !repoName) {
      setExportState("Add a token, repo name, and generated dataset first.");
      return;
    }
    setExportState("Publishing dataset to HuggingFace Hub...");
    try {
      const response = await exportToHuggingFace(dataset, hfToken, repoName);
      setExportState(`Published: ${response.url}`);
    } catch (error) {
      setExportState(error.message);
    }
  }

  const login = useGoogleLogin({
    scope: "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive.file",
    onSuccess: async (tokenResponse) => {
      setGoogleExportState("Pushing dataset to Google Sheets...");
      try {
        const response = await exportToGoogleSheets(dataset, tokenResponse.access_token);
        setGoogleExportState(`Published: ${response.url}`);
        window.open(response.url, "_blank");
      } catch (error) {
        setGoogleExportState(error.message);
      }
    },
    onError: () => setGoogleExportState("Google Login Failed"),
  });

  async function handleGoogleExport() {
    if (!dataset.length) {
      setGoogleExportState("Add a generated dataset first.");
      return;
    }
    login();
  }

  return (
    <section className="rounded-2xl bg-gradient-to-br from-white/70 to-emerald-50/40 backdrop-blur-sm p-5 shadow-[0_4px_24px_rgba(0,100,100,0.22)]">
      <div className="mb-4">
        <h2 className="text-lg font-bold text-slate-800">Download and Export</h2>
        <p className="mt-1 text-sm text-slate-500">Export the dataset, share the config, or push to HuggingFace Hub.</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <button className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-bold text-white hover:bg-slate-800 transition shadow-lg shadow-slate-900/20" onClick={handleCsv}>
          Download CSV
        </button>
        <button className="rounded-xl bg-white/50 px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-white transition shadow-[0_1px_8px_rgba(0,100,100,0.14)]" onClick={handleJson}>
          Download Fairness Report
        </button>
        <button className="rounded-xl bg-white/50 px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-white transition shadow-[0_1px_8px_rgba(0,100,100,0.14)]" onClick={handleShare}>
          Share Config
        </button>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
        <input
          className="rounded-lg border border-slate-200/60 bg-white/60 px-3 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-slate-400"
          placeholder="HuggingFace token"
          value={hfToken}
          onChange={(event) => setHfToken(event.target.value)}
        />
        <input
          className="rounded-lg border border-slate-200/60 bg-white/60 px-3 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-slate-400"
          placeholder="Repo name, e.g. username/de.bias-demo"
          value={repoName}
          onChange={(event) => setRepoName(event.target.value)}
        />
        <button className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white hover:bg-slate-800 transition shadow-lg shadow-slate-900/20" onClick={handleExport}>
          Push to Hub
        </button>
      </div>

      <div className="mt-5 flex gap-3">
        <button className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white hover:bg-slate-800 transition shadow-lg shadow-slate-900/20" onClick={handleGoogleExport}>
          Sign in with Google to Export to Sheets
        </button>
      </div>

      {shareState ? <p className="mt-3 text-sm font-medium text-emerald-600">{shareState}</p> : null}
      {exportState ? <p className="mt-2 break-all text-sm text-slate-500">{exportState}</p> : null}
      {googleExportState ? <p className="mt-2 break-all text-sm text-slate-500">{googleExportState}</p> : null}
    </section>
  );
}

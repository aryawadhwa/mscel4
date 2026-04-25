const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function generateDataset(schema, config, onStatusChange, signal) {
  const statusMessages = [
    "Fitting SDV synthesizer...",
    "Sampling base records...",
    "Applying historical bias correction...",
    "Enforcing representation constraints...",
    "Correcting label bias...",
    "Injecting measurement noise parity...",
    "Computing fairness metrics...",
  ];

  statusMessages.forEach((message, index) => {
    window.setTimeout(() => onStatusChange?.(message), index * 240);
  });

  const response = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ schema, config }),
  });

  if (!response.ok) {
    throw new Error("Generation request failed");
  }

  return response.json();
}

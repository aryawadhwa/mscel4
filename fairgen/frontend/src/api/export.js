const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function exportToHuggingFace(dataset, hfToken, repoName) {
  const response = await fetch(`${API_BASE}/export/huggingface`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ dataset, hfToken, repoName }),
  });

  if (!response.ok) {
    let message = "HuggingFace export failed";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = "HuggingFace export failed";
    }
    throw new Error(message);
  }

  return response.json();
}

export async function exportToGoogleSheets(dataset, accessToken) {
  const response = await fetch(`${API_BASE}/export/googlesheets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ dataset, accessToken }),
  });

  if (!response.ok) {
    let message = "Google Sheets export failed";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((err) => `${err.loc.join(".")}: ${err.msg}`).join(", ");
      } else {
        message = JSON.stringify(payload.detail) || message;
      }
    } catch {
      message = "Google Sheets export failed";
    }
    throw new Error(message);
  }

  return response.json();
}

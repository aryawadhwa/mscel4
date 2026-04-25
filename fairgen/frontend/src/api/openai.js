const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function applyAIConstraint(instruction, currentConfig) {
  const response = await fetch(`${API_BASE}/prompt`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ instruction, currentConfig }),
  });

  if (!response.ok) {
    throw new Error("AI constraint request failed");
  }

  return response.json();
}

export async function testApiConnection() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("Health check failed");
  }
  return response.json();
}

export async function suggestColumns(description, alreadySelected) {
  const response = await fetch(`${API_BASE}/suggest-columns`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ description, alreadySelected }),
  });

  if (!response.ok) {
    throw new Error("Column suggestion request failed");
  }

  return response.json();
}

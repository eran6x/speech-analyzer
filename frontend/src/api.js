// Backend calls. The base URL can be overridden with VITE_API_BASE.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchTopic({ tailored = false, category = null } = {}) {
  const params = new URLSearchParams();
  if (tailored) params.set("tailored", "true");
  if (category) params.set("category", category);
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/topic${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`Failed to fetch topic (${res.status})`);
  return res.json();
}

export async function fetchCategories() {
  const res = await fetch(`${API_BASE}/categories`);
  if (!res.ok) throw new Error(`Failed to fetch categories (${res.status})`);
  return res.json();
}

export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error(`Failed to fetch sessions (${res.status})`);
  return res.json();
}

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`Failed to fetch stats (${res.status})`);
  return res.json();
}

export function audioUrl(sessionId) {
  return `${API_BASE}/sessions/${sessionId}/audio`;
}

export async function analyze(audioBlob, topic, opts = {}) {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("topic_category", topic.category);
  form.append("topic_prompt", topic.prompt);
  form.append("enable_coaching", opts.coaching === false ? "false" : "true");
  form.append("keep_recording", opts.keepRecording === false ? "false" : "true");

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Analysis failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function deleteAllSessions() {
  const res = await fetch(`${API_BASE}/sessions`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete sessions (${res.status})`);
  return res.json();
}

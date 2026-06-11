// Backend calls. The base URL can be overridden with VITE_API_BASE.
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function fetchTopic(tailored = false) {
  const url = tailored ? `${API_BASE}/topic?tailored=true` : `${API_BASE}/topic`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch topic (${res.status})`);
  return res.json();
}

export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error(`Failed to fetch sessions (${res.status})`);
  return res.json();
}

export async function analyze(audioBlob, topic) {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("topic_category", topic.category);
  form.append("topic_prompt", topic.prompt);

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

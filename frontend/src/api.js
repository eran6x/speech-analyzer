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

export async function fetchProfiles() {
  const res = await fetch(`${API_BASE}/profiles`);
  if (!res.ok) throw new Error(`Failed to fetch profiles (${res.status})`);
  return res.json();
}

export async function recoach(sessionId, { target = "", tone = "", depth = "" } = {}) {
  const params = new URLSearchParams();
  if (target) params.set("target", target);
  if (tone) params.set("tone", tone);
  if (depth) params.set("depth", depth);
  const qs = params.toString();
  const res = await fetch(
    `${API_BASE}/sessions/${sessionId}/coach${qs ? `?${qs}` : ""}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error(`Re-coach failed (${res.status})`);
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

export function idealAudioUrl(sessionId) {
  return `${API_BASE}/sessions/${sessionId}/ideal/audio`;
}

async function detail(res, fallback) {
  try {
    return (await res.json()).detail || fallback;
  } catch {
    return fallback;
  }
}

export async function generateIdeal(sessionId, opts = {}) {
  const params = new URLSearchParams();
  if (opts.provider) params.set("provider", opts.provider);
  if (opts.model) params.set("model", opts.model);
  if (opts.voice) params.set("voice", opts.voice);
  const qs = params.toString();
  const res = await fetch(
    `${API_BASE}/sessions/${sessionId}/ideal${qs ? `?${qs}` : ""}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error(await detail(res, `Generation failed (${res.status})`));
  return res.json();
}

export async function getVoice() {
  const res = await fetch(`${API_BASE}/voice`);
  if (!res.ok) throw new Error(`Failed to read voice status (${res.status})`);
  return res.json();
}

export async function enrollVoice(audioBlob) {
  const form = new FormData();
  form.append("audio", audioBlob, "voice.webm");
  const res = await fetch(`${API_BASE}/voice`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await detail(res, `Enrollment failed (${res.status})`));
  return res.json();
}

export async function deleteVoice() {
  const res = await fetch(`${API_BASE}/voice`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete voice (${res.status})`);
  return res.json();
}

export async function analyze(audioBlob, topic, opts = {}) {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("topic_category", topic.category);
  form.append("topic_prompt", topic.prompt);
  form.append("enable_coaching", opts.coaching === false ? "false" : "true");
  form.append("keep_recording", opts.keepRecording === false ? "false" : "true");
  if (opts.coachingTarget) form.append("coaching_target", opts.coachingTarget);
  if (opts.coachingTone) form.append("coaching_tone", opts.coachingTone);
  if (opts.coachingDepth) form.append("coaching_depth", opts.coachingDepth);
  if (opts.parentId) form.append("parent_id", opts.parentId);

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

export async function deleteRecordings() {
  const res = await fetch(`${API_BASE}/recordings`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete recordings (${res.status})`);
  return res.json();
}

export async function updateTranscript(sessionId, transcript) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/transcript`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });
  if (!res.ok) throw new Error(`Failed to save transcript (${res.status})`);
  return res.json();
}

// Local settings store (browser localStorage). These are future-proof
// placeholders — most don't affect analysis yet; see Phase3_plan.md.
const KEY = "speech-analyzer-settings";

export const DEFAULTS = {
  displayName: "",
  email: "",
  keepRecordings: true,
  coachingEnabled: true,
  targetPaceWpm: 145,
  goalOverall: 80, // target average overall score
  goalWeekly: 3, // target sessions per week
  // Voice generation ("ideal delivery"). Empty = backend env default.
  ttsProvider: "", // "" | local | elevenlabs | openai
  ttsModel: "",
  ttsVoice: "",
};

export function loadSettings() {
  try {
    return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY)) || {}) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveSettings(settings) {
  localStorage.setItem(KEY, JSON.stringify(settings));
}

import { useEffect, useRef, useState } from "react";

// 10s is a guideline, not a hard floor — short clips are allowed for testing.
const GUIDE_MIN_SEC = 10;
const MAX_SEC = 60;

export default function Recorder({ onRecorded, disabled }) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [device, setDevice] = useState(null);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const streamRef = useRef(null);

  // Stop everything when the component unmounts.
  useEffect(() => () => stopTimer(), []);

  function stopTimer() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      // The active input device label is available once permission is granted.
      const track = stream.getAudioTracks()[0];
      setDevice(track?.label || "Unknown input device");

      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        streamRef.current?.getTracks().forEach((t) => t.stop());
        onRecorded(blob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setElapsed(0);

      timerRef.current = setInterval(() => {
        setElapsed((prev) => {
          const next = prev + 1;
          if (next >= MAX_SEC) stop(); // auto-stop at the cap
          return next;
        });
      }, 1000);
    } catch (err) {
      setError("Microphone access denied or unavailable.");
    }
  }

  function stop() {
    stopTimer();
    setRecording(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }

  const belowGuide = elapsed < GUIDE_MIN_SEC;

  return (
    <div className="card recorder">
      <div className={`timer ${recording ? "live" : ""}`}>
        {elapsed}s <span className="timer-range">/ aim for {GUIDE_MIN_SEC}–{MAX_SEC}s</span>
      </div>

      {!recording ? (
        <button onClick={start} disabled={disabled} className="primary-btn">
          ● Record
        </button>
      ) : (
        // Stop is always enabled so short test clips are possible; the guide
        // minimum is only a hint.
        <button onClick={stop} className="primary-btn stop" title="Stop and analyze">
          ■ Stop & Analyze {belowGuide ? `(${elapsed}s)` : ""}
        </button>
      )}

      {device && (
        <p className="device" title="Active audio input">
          🎤 {device}
        </p>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default function TopicCard({ topic, onShuffle, onTailor, disabled }) {
  if (!topic) return null;
  return (
    <div className="card topic-card">
      <div className="topic-header">
        <span className="topic-category">{topic.category}</span>
        <div className="topic-actions">
          <button onClick={onShuffle} disabled={disabled} className="link-btn">
            shuffle
          </button>
          <button
            onClick={onTailor}
            disabled={disabled}
            className="link-btn"
            title="Suggest a topic targeting your weakest dimension"
          >
            ✨ tailor to weak areas
          </button>
        </div>
      </div>
      <p className="topic-prompt">{topic.prompt}</p>
    </div>
  );
}

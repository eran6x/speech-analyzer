export default function TopicCard({ topic, onShuffle, disabled }) {
  if (!topic) return null;
  return (
    <div className="card topic-card">
      <div className="topic-header">
        <span className="topic-category">{topic.category}</span>
        <button onClick={onShuffle} disabled={disabled} className="link-btn">
          shuffle
        </button>
      </div>
      <p className="topic-prompt">{topic.prompt}</p>
    </div>
  );
}

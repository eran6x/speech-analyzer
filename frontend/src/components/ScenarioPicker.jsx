export default function ScenarioPicker({
  categories,
  selected,
  onPick,
  onTailor,
  disabled,
}) {
  return (
    <div className="scenarios">
      {categories.map((c) => (
        <button
          key={c}
          className={selected === c ? "scenario active" : "scenario"}
          onClick={() => onPick(c)}
          disabled={disabled}
        >
          {c}
        </button>
      ))}
      <button
        className="scenario tailor"
        onClick={onTailor}
        disabled={disabled}
        title="Suggest a topic targeting your weakest dimension"
      >
        ✨ tailor to weak areas
      </button>
    </div>
  );
}

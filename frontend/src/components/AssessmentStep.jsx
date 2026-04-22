import styles from './AssessmentStep.module.css';

export default function AssessmentStep({ questions, answers, onChange }) {
  if (!questions || questions.length === 0) {
    return <p className={styles.empty}>No questions for this step.</p>;
  }

  return (
    <div className={styles.step}>
      {questions.map((q) => (
        <QuestionField
          key={q.id}
          question={q}
          value={getAnswerValue(q, answers)}
          onChange={(val) => onChange(buildAnswer(q, val))}
        />
      ))}
    </div>
  );
}

function getAnswerValue(q, answers) {
  if (!q.maps_to?.length) return undefined;
  return answers[q.maps_to[0]];
}

function buildAnswer(q, val) {
  const out = {};
  if (!q.maps_to?.length) return out;
  // For single-field questions, set the first mapped field
  if (q.maps_to.length === 1) {
    out[q.maps_to[0]] = val;
  } else if (q.response_type === 'text') {
    // Height/weight is handled specially by the server
    out[q.maps_to[0]] = val;
  } else {
    // For multi-field choice questions, set based on option key
    out[q.maps_to[0]] = val;
  }
  return out;
}

function QuestionField({ question: q, value, onChange }) {
  const label = q.text.split('\n')[0]; // first line as label
  const hint = q.text.split('\n').slice(1).join('\n').trim();

  return (
    <div className={styles.field}>
      <label className={styles.label}>
        {label}
        {q.required && <span className={styles.required}>*</span>}
      </label>
      {hint && <p className={styles.hint}>{hint.replace(/\*\*([^*]+)\*\*/g, '$1')}</p>}

      {q.response_type === 'choice' && (
        <ChoiceInput options={q.options} optionKeys={q.option_keys} value={value} onChange={onChange} />
      )}
      {q.response_type === 'yes_no' && (
        <ChoiceInput options={q.options || ['Yes', 'No']} optionKeys={q.option_keys || ['yes', 'no']} value={value} onChange={onChange} />
      )}
      {q.response_type === 'numeric' && (
        <NumericInput value={value} onChange={onChange} unit={q.unit_hint} />
      )}
      {q.response_type === 'scale' && (
        <ScaleInput value={value} onChange={onChange} />
      )}
      {q.response_type === 'text' && (
        <TextInput value={value} onChange={onChange} />
      )}
    </div>
  );
}

function ChoiceInput({ options, optionKeys, value, onChange }) {
  return (
    <div className={styles.choices}>
      {options.map((opt, i) => {
        const key = optionKeys?.[i] || opt.toLowerCase();
        const selected = value === key;
        return (
          <button
            key={key}
            type="button"
            className={`${styles.choice} ${selected ? styles.selected : ''}`}
            onClick={() => onChange(key)}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function NumericInput({ value, onChange, unit }) {
  return (
    <div className={styles.numericWrapper}>
      <input
        type="number"
        className={styles.numericInput}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
        min={0}
      />
      {unit && <span className={styles.unit}>{unit}</span>}
    </div>
  );
}

function ScaleInput({ value, onChange }) {
  const labels = ['Very calm', 'Calm', 'Moderate', 'Stressed', 'Very stressed'];
  return (
    <div className={styles.scale}>
      <div className={styles.scaleDots}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            className={`${styles.scaleDot} ${value === n ? styles.scaleSelected : ''}`}
            onClick={() => onChange(n)}
            title={labels[n - 1]}
          >
            {n}
          </button>
        ))}
      </div>
      <div className={styles.scaleLabels}>
        <span>😌 Calm</span>
        <span>😰 Stressed</span>
      </div>
    </div>
  );
}

function TextInput({ value, onChange }) {
  return (
    <input
      type="text"
      className={styles.textInput}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value || undefined)}
      placeholder="Type your answer…"
    />
  );
}

import { motion, useReducedMotion } from 'framer-motion';

function bandColor(score) {
  if (score < 35) return 'var(--severity-low)';
  if (score < 70) return 'var(--severity-med)';
  return 'var(--severity-high)';
}

export default function SeverityGauge({ score, label, minutes }) {
  const reduceMotion = useReducedMotion();
  const color = bandColor(score);
  const radius = 92;
  const circumference = Math.PI * radius;

  return (
    <div className="gauge-wrap" style={{ '--gauge-color': color }}>
      <svg viewBox="0 0 240 145" role="img" aria-label={`Severity score ${score} out of 100`}>
        <path
          className="gauge-track"
          d="M 28 122 A 92 92 0 0 1 212 122"
          pathLength="1"
        />
        <motion.path
          key={score}
          className="gauge-fill"
          d="M 28 122 A 92 92 0 0 1 212 122"
          pathLength="1"
          initial={reduceMotion ? { pathLength: score / 100 } : { pathLength: 0 }}
          animate={{ pathLength: score / 100 }}
          transition={{ duration: reduceMotion ? 0 : 0.65, ease: 'easeOut' }}
          style={{ strokeDasharray: circumference }}
        />
      </svg>
      <div className="gauge-value">
        <strong className="numeric">{score}</strong>
        <span>{label}</span>
        {minutes != null && (
          <small className="numeric">
            {minutes >= 60
              ? `~${Math.floor(minutes / 60)}h ${Math.round(minutes % 60)}m predicted clearance`
              : `~${Math.round(minutes)}min predicted clearance`}
          </small>
        )}
      </div>
    </div>
  );
}

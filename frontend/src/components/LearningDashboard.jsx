import { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const formatNumber = (value) => value == null ? '—' : Number(value).toLocaleString();

export default function LearningDashboard({ api, onFailure }) {
  const [overview, setOverview] = useState(null);
  const [errors, setErrors] = useState(null);
  const [causes, setCauses] = useState([]);
  const [heatmap, setHeatmap] = useState(null);
  const [retraining, setRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const responses = await Promise.all([
          fetch(`${api}/api/learning/overview`),
          fetch(`${api}/api/learning/error-by-corridor`),
          fetch(`${api}/api/learning/cause-volume`),
          fetch(`${api}/api/learning/time-heatmap`),
        ]);
        if (responses.some((response) => !response.ok)) throw new Error('Learning data failed');
        const [overviewData, errorData, causeData, heatmapData] = await Promise.all(
          responses.map((response) => response.json()),
        );
        setOverview(overviewData);
        setErrors(errorData);
        setCauses(causeData);
        setHeatmap(heatmapData);
      } catch (error) {
        console.error(error);
        onFailure();
      }
    };
    loadDashboard();
  }, [api, onFailure]);

  const errorData = useMemo(
    () => (errors?.corridors || []).map((corridor, index) => ({
      corridor,
      error: errors.mean_error_min[index],
    })),
    [errors],
  );
  const maxHeat = Math.max(1, ...(heatmap?.counts || []).flat());

  const retrain = async () => {
    setRetraining(true);
    const before = overview?.model_mae;
    try {
      const response = await fetch(`${api}/api/retrain`, { method: 'POST' });
      if (!response.ok) throw new Error('Retraining failed');
      const data = await response.json();
      if (data.status !== 'ok') throw new Error(data.stderr || 'Retraining failed');
      setRetrainResult({ before, after: data.metadata.mae });
      setOverview((current) => ({
        ...current,
        model_mae: data.metadata.mae,
        model_r2: data.metadata.r2,
        model_trained_on: data.metadata.trained_at,
      }));
    } catch (error) {
      console.error(error);
      onFailure();
    } finally {
      setRetraining(false);
    }
  };

  const metrics = [
    ['Total events', overview?.total_events],
    ['Closed events', overview?.closed_events],
    ['Avg resolution', overview ? `${formatNumber(overview.avg_resolution_min)} min` : null],
    ['High severity', overview?.high_severity_events],
  ];

  return (
    <section className="learning-dashboard">
      <div className="learning-heading">
        <div>
          <p className="eyebrow">Model observatory</p>
          <h1>Learning dashboard</h1>
          <p>Historical operating volume, error patterns, and retraining controls.</p>
        </div>
        <div className="retrain-box">
          <span>MAE <strong className="numeric">{formatNumber(overview?.model_mae)}</strong></span>
          <span>R² <strong className="numeric">{overview?.model_r2 == null ? '—' : overview.model_r2.toFixed(3)}</strong></span>
          <button className="primary-button" onClick={retrain} disabled={retraining}>
            <RefreshCw size={16} className={retraining ? 'spin' : ''} />
            {retraining ? 'Retraining' : 'Retrain'}
          </button>
          {retrainResult && (
            <small>MAE: {formatNumber(retrainResult.before)} → {formatNumber(retrainResult.after)}</small>
          )}
        </div>
      </div>

      <div className="learning-metrics">
        {metrics.map(([label, value]) => (
          <article className="glass-panel" key={label}>
            <span>{label}</span>
            <strong className="numeric">{value ?? '—'}</strong>
          </article>
        ))}
      </div>

      <div className="chart-grid">
        <article className="glass-panel chart-card wide">
          <h3>Mean prediction error by corridor</h3>
          <p>Positive values indicate under-predicted closure time.</p>
          <ResponsiveContainer width="100%" height={310}>
            <BarChart data={errorData} margin={{ left: 10, right: 10, bottom: 65 }}>
              <CartesianGrid stroke="rgba(255,255,255,.06)" vertical={false} />
              <XAxis dataKey="corridor" angle={-35} textAnchor="end" interval={0} tick={{ fill: '#94A3B8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,.1)' }} />
              <Bar dataKey="error" fill="#F5A524" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-panel chart-card">
          <h3>Cause volume vs duration</h3>
          <p>Event count against median closure minutes.</p>
          <ResponsiveContainer width="100%" height={310}>
            <ScatterChart margin={{ left: 8, right: 16, bottom: 15 }}>
              <CartesianGrid stroke="rgba(255,255,255,.06)" />
              <XAxis type="number" dataKey="count" name="Events" tick={{ fill: '#94A3B8', fontSize: 11 }} />
              <YAxis type="number" dataKey="median" name="Median minutes" tick={{ fill: '#94A3B8', fontSize: 11 }} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,.1)' }}
              />
              <Scatter name="Causes" data={causes} fill="#38BDF8" />
            </ScatterChart>
          </ResponsiveContainer>
        </article>

        <article className="glass-panel chart-card heatmap-card">
          <h3>Event volume by day and hour</h3>
          <p>Darker amber cells represent busier periods.</p>
          <div className="heatmap">
            <span />
            {(heatmap?.hours || []).map((hour) => <small key={hour}>{hour % 3 === 0 ? hour : ''}</small>)}
            {(heatmap?.days || []).map((day, dayIndex) => (
              <div className="heatmap-row" key={day}>
                <strong>{day}</strong>
                {heatmap.counts[dayIndex].map((count, hour) => (
                  <span
                    key={`${day}-${hour}`}
                    title={`${day} ${hour}:00 — ${count} events`}
                    style={{ '--intensity': count / maxHeat }}
                  />
                ))}
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}

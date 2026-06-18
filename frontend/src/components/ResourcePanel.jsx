import { Construction, RadioTower, ShieldCheck, Users } from 'lucide-react';

export default function ResourcePanel({ result }) {
  if (!result) {
    return (
      <section className="glass-panel empty-state">
        <RadioTower size={28} />
        <h3>No active assessment</h3>
        <p>Submit an event or choose a scenario to prepare the command brief.</p>
      </section>
    );
  }

  return (
    <section className="glass-panel resource-panel">
      <div className="resource-metrics">
        <article>
          <Users />
          <span>Officers</span>
          <strong className="numeric">{result.officers_needed}</strong>
        </article>
        <article>
          <Construction />
          <span>Barricade points</span>
          <strong className="numeric">{result.estimated_barricade_points}</strong>
        </article>
        <article>
          <ShieldCheck />
          <span>Confidence</span>
          <strong className="numeric">{Math.round(result.barricade_confidence * 100)}%</strong>
        </article>
      </div>

      <div className="resource-section">
        <div className="section-heading">
          <h3>Recommended stations</h3>
          <span className={`status-pill ${result.barricade_needed ? 'danger' : 'safe'}`}>
            Barricades {result.barricade_needed ? 'required' : 'optional'}
          </span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Station</th><th>Distance</th><th>Load</th></tr>
            </thead>
            <tbody>
              {result.recommended_stations.map((station) => (
                <tr key={station.name}>
                  <td>{station.name}{station.is_primary && <small>Primary</small>}</td>
                  <td className="numeric">{station.distance_km} km</td>
                  <td className="numeric">{station.current_load}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <blockquote>{result.human_instruction}</blockquote>
    </section>
  );
}

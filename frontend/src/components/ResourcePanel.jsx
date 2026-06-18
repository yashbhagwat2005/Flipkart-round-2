import { Construction, RadioTower, ShieldCheck, Users } from 'lucide-react';

export default function ResourcePanel({ result }) {
  if (!result) {
    return (
      <section className="glass-panel empty-state">
        <RadioTower size={28} />
        <h3>Awaiting incident data</h3>
        <p>Choose a demo scenario above or fill in the incident form to generate
           a deployment plan with officer counts, station assignments, and
           barricade recommendations.</p>
      </section>
    );
  }

  return (
    <section className="glass-panel resource-panel">
      <div className="resource-metrics">
        <article>
          <Users />
          <span>Officers needed</span>
          <strong className="numeric">{result.officers_needed}</strong>
        </article>
        <article>
          <Construction />
          <span>Barricade locations</span>
          <strong className="numeric">{result.estimated_barricade_points}</strong>
        </article>
        <article>
          <ShieldCheck />
          <span>ML confidence</span>
          <strong className="numeric">{Math.round(result.barricade_confidence * 100)}%</strong>
        </article>
      </div>

      <div className="resource-section">
        <div className="section-heading">
          <h3>Nearest responding stations</h3>
          <span className={`status-pill ${result.barricade_needed ? 'danger' : 'safe'}`}>
            {result.barricade_needed ? '⚠️ Barricades recommended' : '✓ No barricades needed'}
          </span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Police Station</th><th>Distance</th><th>Active events</th></tr>
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

      <div className="instruction-block">
        <span className="instruction-label">📻 Radio dispatch instruction</span>
        <blockquote>{result.human_instruction}</blockquote>
      </div>
    </section>
  );
}

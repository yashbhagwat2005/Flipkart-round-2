import { useEffect, useMemo, useState } from 'react';
import { Activity, CalendarClock, MapPin, Route } from 'lucide-react';

const CAUSES = [
  'public_event',
  'vip_movement',
  'procession',
  'protest',
  'construction',
  'tree_fall',
  'vehicle_breakdown',
  'others',
];

const ZONES = [
  'Central Zone 1',
  'Central Zone 2',
  'East Zone',
  'West Zone',
  'North Zone',
  'South Zone',
  'North East Zone',
  'South East Zone',
  'Whitefield Zone',
  'Unknown',
];

// Fallback zone mapping per node ID (used before nodeData is loaded)
const NODE_ZONE = {
  CBD: 'Central Zone 2',
  Mekhri_Circle: 'Central Zone 1',
  Hebbal: 'North Zone',
  Yeshwanthpura: 'West Zone',
  Jalahalli: 'West Zone',
  Kengeri: 'West Zone',
  Vijayanagar: 'West Zone',
  Jayanagar: 'South Zone',
  Silk_Board: 'South East Zone',
  Koramangala: 'South East Zone',
  KR_Puram: 'East Zone',
  Nagavara: 'North East Zone',
  Yelahanka: 'North Zone',
  Electronic_City: 'South East Zone',
  Whitefield: 'Whitefield Zone',
  Bannerghatta: 'South Zone',
};

const DEFAULT_FORM = {
  event_cause: 'public_event',
  corridor: 'CBD 2',
  zone: 'Central Zone 2',
  priority: 'High',
  requires_road_closure_bool: 0,
  hour: 19,
  dow: 3,
  latitude: 12.9784,
  longitude: 77.5996,
  crowd_size: 45000,
  junction: 'Chinnaswamy Stadium',
  blocked_corridor: 'CBD 2',
  origin: 'CBD',
  destination: 'KR_Puram',
  planned: true,
};

const scenarioDefaults = [
  { event_cause: 'vehicle_breakdown', priority: 'High', crowd_size: 0 },
  { event_cause: 'vip_movement', priority: 'High', crowd_size: 12000 },
  { event_cause: 'procession', priority: 'High', crowd_size: 25000 },
];

export default function EventForm({
  scenarios,
  corridors,
  nodes,        // {id -> name} for dropdown labels
  nodeData,     // {id -> {lat, lon, name}} full objects from /api/state
  selectedScenario,
  onScenario,
  onSubmit,
  submitting,
}) {
  const [form, setForm] = useState(DEFAULT_FORM);
  const nodeEntries = useMemo(() => Object.entries(nodes), [nodes]);

  // When full node data first loads, sync the default origin lat/lon
  useEffect(() => {
    if (nodeData && nodeData[form.origin]) {
      const nd = nodeData[form.origin];
      if (nd.lat !== undefined) {
        setForm((f) => ({ ...f, latitude: nd.lat, longitude: nd.lon }));
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Boolean(nodeData && Object.keys(nodeData).length)]);

  const resolveNodeCoords = (id) => {
    if (nodeData && nodeData[id]) return { lat: nodeData[id].lat, lon: nodeData[id].lon };
    return null;
  };

  const update = (field, value) => {
    setForm((current) => {
      const patch = { [field]: value };

      // Sync blocked_corridor + junction when corridor changes
      if (field === 'corridor') {
        patch.blocked_corridor = value;
        patch.junction = value;
      }

      // Auto-fill lat/lon + zone from origin node
      if (field === 'origin') {
        const coords = resolveNodeCoords(value);
        if (coords) {
          patch.latitude = coords.lat;
          patch.longitude = coords.lon;
        }
        patch.zone = NODE_ZONE[value] || 'Unknown';
        patch.junction = nodes[value] || value;
      }

      return { ...current, ...patch };
    });
  };

  const selectScenario = (scenario, index) => {
    const origin = scenario.origin;
    const coords = resolveNodeCoords(origin);
    setForm((current) => ({
      ...current,
      ...scenarioDefaults[index],
      corridor: scenario.blocked,
      blocked_corridor: scenario.blocked,
      origin,
      destination: scenario.dest,
      zone: NODE_ZONE[origin] || current.zone,
      latitude: coords ? coords.lat : current.latitude,
      longitude: coords ? coords.lon : current.longitude,
      junction: nodes[origin] || origin,
    }));
    onScenario(index);
  };

  const submit = (event) => {
    event.preventDefault();
    const { planned, ...payload } = form;
    onSubmit(payload);
  };

  return (
    <aside className="glass-panel event-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Command intake</p>
          <h2>Analyze an event</h2>
        </div>
        <Activity size={20} />
      </div>

      <div className="scenario-strip">
        {scenarios.map((scenario, index) => (
          <button
            type="button"
            key={scenario.desc}
            className={`scenario-card ${selectedScenario === index ? 'active' : ''}`}
            onClick={() => selectScenario(scenario, index)}
          >
            <Route size={15} />
            <span>{scenario.desc}</span>
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="event-form">
        <div className="field-grid">
          <label>
            Event cause
            <select value={form.event_cause} onChange={(e) => update('event_cause', e.target.value)}>
              {CAUSES.map((cause) => <option key={cause}>{cause}</option>)}
            </select>
          </label>
          <label>
            Priority
            <select value={form.priority} onChange={(e) => update('priority', e.target.value)}>
              {['Low', 'Medium', 'High'].map((priority) => <option key={priority}>{priority}</option>)}
            </select>
          </label>
        </div>

        <label>
          Corridor / blocked corridor
          <select value={form.corridor} onChange={(e) => update('corridor', e.target.value)}>
            {!corridors.includes('CBD 2') && <option>CBD 2</option>}
            {corridors.map((corridor) => <option key={corridor}>{corridor}</option>)}
          </select>
        </label>

        <label>
          Zone
          <select value={form.zone} onChange={(e) => update('zone', e.target.value)}>
            {ZONES.map((zone) => <option key={zone}>{zone}</option>)}
          </select>
        </label>

        <div className="field-grid">
          <label>
            Origin
            <select value={form.origin} onChange={(e) => update('origin', e.target.value)}>
              {nodeEntries.map(([id, name]) => <option value={id} key={id}>{name}</option>)}
            </select>
          </label>
          <label>
            Destination
            <select value={form.destination} onChange={(e) => update('destination', e.target.value)}>
              {nodeEntries.map(([id, name]) => <option value={id} key={id}>{name}</option>)}
            </select>
          </label>
        </div>

        <div className="field-grid">
          <label>
            Day
            <select value={form.dow} onChange={(e) => update('dow', Number(e.target.value))}>
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => (
                <option value={index} key={day}>{day}</option>
              ))}
            </select>
          </label>
          <label>
            Crowd size
            <input
              type="number"
              min="0"
              step="1000"
              value={form.crowd_size}
              onChange={(e) => update('crowd_size', Number(e.target.value))}
            />
          </label>
        </div>

        <label className="range-field">
          <span>Event hour <strong className="numeric">{String(form.hour).padStart(2, '0')}:00</strong></span>
          <input
            type="range"
            min="0"
            max="23"
            value={form.hour}
            onChange={(e) => update('hour', Number(e.target.value))}
          />
        </label>

        {/* Coordinates — auto-populated from origin node, editable for precision placement */}
        <div className="field-grid">
          <label>
            <span className="coord-label"><MapPin size={11} /> Latitude</span>
            <input
              type="number"
              step="0.0001"
              value={form.latitude}
              onChange={(e) => update('latitude', Number(e.target.value))}
            />
          </label>
          <label>
            <span className="coord-label"><MapPin size={11} /> Longitude</span>
            <input
              type="number"
              step="0.0001"
              value={form.longitude}
              onChange={(e) => update('longitude', Number(e.target.value))}
            />
          </label>
        </div>

        <div className="toggle-row">
          <span><CalendarClock size={16} /> Event planning</span>
          <div className="segmented">
            <button type="button" className={form.planned ? 'active' : ''} onClick={() => update('planned', true)}>Planned</button>
            <button type="button" className={!form.planned ? 'active' : ''} onClick={() => update('planned', false)}>Unplanned</button>
          </div>
        </div>

        <button className="primary-button" disabled={submitting || !nodeEntries.length}>
          {submitting ? <><span className="spinner" /> Analyzing</> : 'Run operational analysis'}
        </button>
      </form>
    </aside>
  );
}

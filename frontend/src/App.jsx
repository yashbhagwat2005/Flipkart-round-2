import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { BrainCircuit, Map, ShieldAlert, Siren, X } from 'lucide-react';

import DiversionMap from './components/DiversionMap';
import EventForm from './components/EventForm';
import LearningDashboard from './components/LearningDashboard';
import ResourcePanel from './components/ResourcePanel';
import SeverityGauge from './components/SeverityGauge';

const API = 'http://127.0.0.1:8000';

const views = [
  { id: 'report', label: 'Situation Report', icon: Siren },
  { id: 'map', label: 'Diversion Map', icon: Map },
  { id: 'learning', label: 'Learning Dashboard', icon: BrainCircuit },
];

export default function App() {
  const [view, setView] = useState('report');
  const [networkError, setNetworkError] = useState('');
  const [state, setState] = useState(null);
  const [corridors, setCorridors] = useState([]);
  // nodes: {id -> name} for dropdown labels
  const [nodes, setNodes] = useState({});
  // nodeData: {id -> {lat, lon, name}} full objects for lat/lon auto-fill
  const [nodeData, setNodeData] = useState({});
  const [eventResult, setEventResult] = useState(null);
  const [scenarioRoute, setScenarioRoute] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const reduceMotion = useReducedMotion();

  const reportFailure = useCallback(() => {
    setNetworkError('Backend unreachable — check the server is running');
  }, []);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [stateResponse, corridorResponse, nodeResponse] = await Promise.all([
          fetch(`${API}/api/state`),
          fetch(`${API}/api/corridors`),
          fetch(`${API}/api/nodes`),
        ]);
        if (!stateResponse.ok || !corridorResponse.ok || !nodeResponse.ok) {
          throw new Error('Backend request failed');
        }
        const [stateData, corridorData, nodeNameData] = await Promise.all([
          stateResponse.json(),
          corridorResponse.json(),
          nodeResponse.json(),
        ]);
        setState(stateData);
        setCorridors(corridorData.corridors);
        setNodes(nodeNameData.nodes);
        // Full node objects (with lat/lon) come from /api/state
        if (stateData.nodes) setNodeData(stateData.nodes);
      } catch (error) {
        console.error(error);
        reportFailure();
      }
    };
    loadInitialData();
  }, []);

  const handleScenario = async (index) => {
    setSelectedScenario(index);
    try {
      const response = await fetch(`${API}/api/scenario/${index}`);
      if (!response.ok) throw new Error('Scenario request failed');
      setScenarioRoute(await response.json());
    } catch (error) {
      console.error(error);
      reportFailure();
    }
  };

  const handleSubmit = async (payload) => {
    setSubmitting(true);
    try {
      const response = await fetch(`${API}/api/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('Event analysis failed');
      const result = await response.json();
      setEventResult(result);
      setSelectedScenario(null);
      if (result.diversion) setView('map');
    } catch (error) {
      console.error(error);
      reportFailure();
    } finally {
      setSubmitting(false);
    }
  };

  const activeRoute = useMemo(
    () => eventResult?.diversion || scenarioRoute,
    [eventResult, scenarioRoute],
  );

  return (
    <div className="app-shell">
      {networkError && (
        <div className="error-banner" role="alert">
          <span>{networkError}</span>
          <button aria-label="Dismiss backend warning" onClick={() => setNetworkError('')}>
            <X size={18} />
          </button>
        </div>
      )}

      <header className="app-header">
        <div className="brand">
          <span className="brand-icon"><ShieldAlert size={24} /></span>
          <div>
            <strong>ASTRAM</strong>
            <span>Traffic Command</span>
          </div>
        </div>
        <nav className="view-switcher" aria-label="Main views">
          {views.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={view === id ? 'active' : ''}
              onClick={() => setView(id)}
            >
              <Icon size={17} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </header>

      <AnimatePresence mode="wait">
        <motion.main
          key={view}
          className={`view view-${view}`}
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduceMotion ? undefined : { opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.22 }}
        >
          {view === 'report' && (
            <div className="report-layout">
              <EventForm
                scenarios={state?.scenarios || []}
                corridors={corridors}
                nodes={nodes}
                nodeData={nodeData}
                selectedScenario={selectedScenario}
                onScenario={handleScenario}
                onSubmit={handleSubmit}
                submitting={submitting}
              />
              <section className="analysis-column">
                <div className="glass-panel severity-panel">
                  <div>
                    <p className="eyebrow">Predicted operational severity</p>
                    <h2>Live impact assessment</h2>
                  </div>
                  <SeverityGauge
                    score={eventResult?.severity_score || 0}
                    label={eventResult?.severity_label || 'Awaiting event'}
                    minutes={eventResult?.predicted_closure_min}
                  />
                </div>
                <ResourcePanel result={eventResult} />
              </section>
            </div>
          )}

          {view === 'map' && (
            <DiversionMap
              networkState={state}
              routeData={activeRoute}
              custom={Boolean(eventResult?.diversion)}
            />
          )}

          {view === 'learning' && (
            <LearningDashboard api={API} onFailure={reportFailure} />
          )}
        </motion.main>
      </AnimatePresence>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Circle, Marker, Popup, useMap } from 'react-leaflet';
import { ShieldAlert, Route, AlertTriangle, Radio, Activity, Navigation2 } from 'lucide-react';
import L from 'leaflet';

// Map auto-fitter component
function MapFitter({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [bounds, map]);
  return null;
}

export default function App() {
  const [state, setState] = useState(null);
  const [activeScenario, setActiveScenario] = useState(0);
  const [routeData, setRouteData] = useState(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/state')
      .then(res => res.json())
      .then(data => setState(data))
      .catch(err => console.error("Error loading state", err));
  }, []);

  useEffect(() => {
    if (state) {
      fetch(`http://127.0.0.1:8000/api/scenario/${activeScenario}`)
        .then(res => res.json())
        .then(data => setRouteData(data))
        .catch(err => console.error("Error loading scenario", err));
    }
  }, [activeScenario, state]);

  if (!state || !routeData) {
    return (
      <div className="dashboard-container" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <Activity className="lucide-spin" size={48} color="var(--accent)" />
      </div>
    );
  }

  // Calculate map bounds based on current routes
  const bounds = [];
  if (routeData.scenario.origin && state.nodes[routeData.scenario.origin]) {
    bounds.push([state.nodes[routeData.scenario.origin].lat, state.nodes[routeData.scenario.origin].lon]);
  }
  if (routeData.scenario.dest && state.nodes[routeData.scenario.dest]) {
    bounds.push([state.nodes[routeData.scenario.dest].lat, state.nodes[routeData.scenario.dest].lon]);
  }
  // Add some fallback bounds for Bengaluru
  if (bounds.length === 0) {
    bounds.push([12.8, 77.4], [13.1, 77.8]);
  }

  // Draw background edges
  const bgEdges = state.edges.map((e, i) => {
    const n1 = state.nodes[e.from];
    const n2 = state.nodes[e.to];
    if(!n1 || !n2) return null;
    // Don't draw background for the blocked route
    if (e.corridor === routeData.scenario.blocked) return null;
    return <Polyline key={`bg-${i}`} positions={[[n1.lat, n1.lon], [n2.lat, n2.lon]]} color="#334155" weight={3} opacity={0.5} />;
  });

  // Draw blocked edges
  const blockedEdges = state.edges.filter(e => e.corridor === routeData.scenario.blocked).map((e, i) => {
    const n1 = state.nodes[e.from];
    const n2 = state.nodes[e.to];
    if(!n1 || !n2) return null;
    return (
      <Polyline 
        key={`blocked-${i}`} 
        positions={[[n1.lat, n1.lon], [n2.lat, n2.lon]]} 
        color="var(--blocked-route)" 
        weight={6} 
      />
    );
  });

  // Draw hotspots
  const hotspots = state.hotspots.map((h, i) => (
    <Circle key={`hs-${i}`} center={[h.lat, h.lon]} radius={1500} pathOptions={{ color: '#8b5cf6', fillColor: '#8b5cf6', fillOpacity: 0.2 }} />
  ));

  // Draw routes
  const drawPath = (pathObj, color, weight, dashArray = null) => {
    if (!pathObj || !pathObj.path) return null;
    return pathObj.path.map((segment, i) => {
      const n1 = state.nodes[segment.from];
      const n2 = state.nodes[segment.to];
      if(!n1 || !n2) return null;
      return (
        <Polyline 
          key={`route-${i}`} 
          positions={[[n1.lat, n1.lon], [n2.lat, n2.lon]]} 
          color={color} 
          weight={weight} 
          dashArray={dashArray} 
        />
      );
    });
  };

  // Create custom icons
  const createIcon = (color, label) => L.divIcon({
    className: 'custom-div-icon',
    html: `<div style="background-color: ${color}; border: 3px solid #1e293b; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-family: sans-serif; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">${label}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });

  const originNode = state.nodes[routeData.scenario.origin];
  const destNode = state.nodes[routeData.scenario.dest];

  return (
    <div className="dashboard-container">
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldAlert size={28} />
          </div>
          <h1>Traffic Manager</h1>
        </div>
        
        <div className="section-title">Active Scenarios</div>
        <div className="scenario-list">
          {state.scenarios.map((s, idx) => (
            <div 
              key={idx} 
              className={`scenario-card ${activeScenario === idx ? 'active' : ''}`}
              onClick={() => setActiveScenario(idx)}
            >
              <h3>{s.desc}</h3>
              <p>{s.blocked} Blocked</p>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="main-content">
        {/* Top Metrics Overlay */}
        <div className="top-overlay">
          <div className="metrics-row">
            <div className="metric-card" style={{ borderLeft: '4px solid var(--blocked-route)' }}>
              <div className="metric-label" style={{ color: 'var(--blocked-route)' }}><AlertTriangle size={14} /> Blocked Corridor</div>
              <div className="metric-value">{routeData.scenario.blocked}</div>
            </div>
            
            <div className="metric-card" style={{ borderLeft: '4px solid var(--primary-route)' }}>
              <div className="metric-label" style={{ color: 'var(--primary-route)' }}><Navigation2 size={14} /> Primary Diversion</div>
              <div className="metric-value">{routeData.primary.distance} km</div>
            </div>

            <div className="metric-card" style={{ borderLeft: '4px solid var(--secondary-route)' }}>
              <div className="metric-label" style={{ color: 'var(--secondary-route)' }}><Route size={14} /> Secondary Backup</div>
              <div className="metric-value">{routeData.secondary.distance} km</div>
            </div>
          </div>
        </div>

        {/* Bottom Instruction Overlay */}
        <div className="bottom-overlay">
          <div className="instruction-panel">
            <div className="instruction-icon">
              <Radio size={32} />
            </div>
            <div className="instruction-content">
              <h3>Radio Dispatch Instruction</h3>
              <p>"{routeData.instruction}"</p>
            </div>
          </div>
        </div>

        {/* MAP */}
        <div className="map-container">
          <MapContainer 
            center={[12.9716, 77.5946]} 
            zoom={12} 
            style={{ height: "100%", width: "100%" }}
            zoomControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com/">CartoDB</a>'
            />
            <MapFitter bounds={bounds} />
            
            {/* Layers */}
            {bgEdges}
            {blockedEdges}
            {hotspots}
            
            {/* We don't have the explicit blocked edge coordinates in API easily, so we just show origin/dest markers */}
            {drawPath(routeData.secondary, 'var(--secondary-route)', 5)}
            {drawPath(routeData.primary, 'var(--primary-route)', 6)}
            
            {originNode && (
              <Marker position={[originNode.lat, originNode.lon]} icon={createIcon('var(--blocked-route)', 'A')}>
                <Popup>{routeData.scenario.origin} (Origin)</Popup>
              </Marker>
            )}
            
            {destNode && (
              <Marker position={[destNode.lat, destNode.lon]} icon={createIcon('var(--primary-route)', 'B')}>
                <Popup>{routeData.scenario.dest} (Destination)</Popup>
              </Marker>
            )}

          </MapContainer>
        </div>
      </div>
    </div>
  );
}

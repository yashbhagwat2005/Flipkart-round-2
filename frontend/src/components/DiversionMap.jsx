import React, { useEffect, useMemo } from 'react';
import L from 'leaflet';
import {
  Circle,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet';
import { AlertTriangle, Navigation2, Radio, Route } from 'lucide-react';

function MapFitter({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds.length > 1) map.fitBounds(bounds, { padding: [60, 60] });
  }, [bounds, map]);
  return null;
}



const markerIcon = (color, label) => L.divIcon({
  className: 'custom-div-icon',
  html: `<div class="map-pin" style="--pin-color:${color}">${label}</div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});



function routeNodes(routeData, custom, type) {
  if (!routeData) return [];
  if (custom) return routeData[`${type}_route`] || [];
  const segments = routeData[type]?.path || [];
  if (!segments.length) return [];
  return [segments[0].from, ...segments.map((segment) => segment.to)];
}

export default function DiversionMap({ networkState, routeData, custom }) {
  const primaryNodes = routeNodes(routeData, custom, 'primary');
  const secondaryNodes = routeNodes(routeData, custom, 'secondary');
  const scenario = custom
    ? {
        blocked: routeData?.blocked_corridor,
        origin: routeData?.origin,
        dest: routeData?.destination,
      }
    : routeData?.scenario;

  const nodeData = networkState?.nodes || {};
  const primaryPositions = useMemo(
    () => primaryNodes.map((node) => [nodeData[node]?.lat, nodeData[node]?.lon]).filter(([lat]) => lat != null),
    [primaryNodes.join('|'), nodeData],
  );
  const secondaryPositions = useMemo(
    () => secondaryNodes.map((node) => [nodeData[node]?.lat, nodeData[node]?.lon]).filter(([lat]) => lat != null),
    [secondaryNodes.join('|'), nodeData],
  );
  const bounds = [...primaryPositions, ...secondaryPositions];
  const primaryDistance = custom ? routeData?.primary_distance_km : routeData?.primary?.distance;
  const secondaryDistance = custom ? routeData?.secondary_distance_km : routeData?.secondary?.distance;
  const instruction = custom ? routeData?.officer_instruction : routeData?.instruction;

  return (
    <section className="map-view">
      <div className="map-overlay metrics-row">
        <article>
          <span><AlertTriangle size={14} /> ⛔ Blocked corridor</span>
          <strong>{scenario?.blocked || 'No route selected'}</strong>
        </article>
        <article>
          <span><Navigation2 size={14} /> Primary route</span>
          <strong className="numeric">{primaryDistance ?? 0} km</strong>
        </article>
        <article>
          <span><Route size={14} /> Secondary route</span>
          <strong className="numeric">{secondaryDistance ?? 0} km</strong>
        </article>
      </div>

      <div className="map-overlay map-legend">
        <p className="eyebrow" style={{ marginBottom: 12 }}>Map Legend</p>
        <ul>
          <li><span className="legend-line blocked" /> Blocked Corridor</li>
          <li><span className="legend-line primary" /> Primary Route</li>
          <li><span className="legend-line secondary" /> Diversion Route</li>
          <li><span className="legend-circle hotspot" /> Congestion Hotspot</li>
        </ul>
      </div>

      <div className="map-overlay instruction-panel">
        <Radio size={24} />
        <div>
          <span>Officer dispatch instruction</span>
          <p>{instruction || 'Select a scenario from the Analyze Event tab, or submit a new incident\n to auto-generate a cascade-aware diversion route.'}</p>
        </div>
      </div>

      <MapContainer center={[12.9716, 77.5946]} zoom={12} zoomControl={false}>
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />
        <MapFitter bounds={bounds} />

        {(networkState?.edges || []).map((edge, index) => {
          const start = nodeData[edge.from];
          const end = nodeData[edge.to];
          if (!start || !end || edge.corridor === scenario?.blocked) return null;
          return (
            <Polyline
              key={`${edge.from}-${edge.to}-${index}`}
              positions={[[start.lat, start.lon], [end.lat, end.lon]]}
              pathOptions={{ color: '#334155', weight: 2, opacity: 0.35 }}
            />
          );
        })}

        {(networkState?.edges || []).filter((edge) => edge.corridor === scenario?.blocked).map((edge, index) => {
          const start = nodeData[edge.from];
          const end = nodeData[edge.to];
          if (!start || !end) return null;
          return (
            <Polyline
              key={`blocked-${index}`}
              positions={[[start.lat, start.lon], [end.lat, end.lon]]}
              pathOptions={{ color: '#E5484D', weight: 6, opacity: 0.9 }}
            />
          );
        })}

        {(networkState?.hotspots || []).map((hotspot, index) => (
          <Circle
            key={`${hotspot.lat}-${index}`}
            center={[hotspot.lat, hotspot.lon]}
            radius={800}
            pathOptions={{ color: '#E5484D', fillColor: '#E5484D', fillOpacity: 0.1 }}
          />
        ))}

        <Polyline 
          positions={secondaryPositions} 
          pathOptions={{ color: '#38BDF8', weight: 5, dashArray: '10 8' }} 
        />
        <Polyline 
          positions={primaryPositions} 
          pathOptions={{ color: '#F5A524', weight: 6 }} 
        />

        {scenario?.origin && nodeData[scenario.origin] && (
          <Marker
            position={[nodeData[scenario.origin].lat, nodeData[scenario.origin].lon]}
            icon={markerIcon('#E5484D', 'A')}
          >
            <Popup>{nodeData[scenario.origin].name}</Popup>
          </Marker>
        )}
        {scenario?.dest && nodeData[scenario.dest] && (
          <Marker
            position={[nodeData[scenario.dest].lat, nodeData[scenario.dest].lon]}
            icon={markerIcon('#F5A524', 'B')}
          >
            <Popup>{nodeData[scenario.dest].name}</Popup>
          </Marker>
        )}
      </MapContainer>
    </section>
  );
}

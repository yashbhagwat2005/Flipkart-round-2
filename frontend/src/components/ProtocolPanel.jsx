import React from 'react';
import { Shield, ShieldAlert, Users, Radio, CheckCircle2 } from 'lucide-react';

export default function ProtocolPanel({ result }) {
  if (!result || !result.police_protocol) return null;

  const { severity_label, police_protocol } = result;
  
  const getIcon = () => {
    switch (severity_label) {
      case 'Critical': return <ShieldAlert size={28} className="text-red-500" style={{color: 'var(--severity-high)'}} />;
      case 'High': return <Shield size={28} style={{color: 'var(--severity-high)'}} />;
      case 'Medium': return <Users size={28} style={{color: 'var(--severity-med)'}} />;
      default: return <CheckCircle2 size={28} style={{color: 'var(--severity-low)'}} />;
    }
  };

  return (
    <div className="glass-panel protocol-panel" style={{ marginTop: '24px', padding: '24px', borderRadius: '18px' }}>
      <div className="panel-heading" style={{ marginBottom: '16px' }}>
        <div>
          <p className="eyebrow">Police Protocol Engine</p>
          <h2>Recommended Action</h2>
        </div>
        {getIcon()}
      </div>
      
      <div style={{ display: 'grid', gap: '16px' }}>
        <div style={{
          padding: '16px',
          background: 'rgba(0,0,0,0.1)',
          borderLeft: `4px solid var(--severity-${severity_label.toLowerCase() === 'critical' ? 'high' : severity_label.toLowerCase() === 'high' ? 'high' : severity_label.toLowerCase() === 'medium' ? 'med' : 'low'})`,
          borderRadius: '0 8px 8px 0'
        }}>
          <h3 style={{ fontSize: '18px', marginBottom: '8px', color: 'var(--text-main)' }}>
            {police_protocol.action}
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
            {police_protocol.reason}
          </p>
        </div>
        
        {police_protocol.requires_action && (
          <button 
            className="primary-button" 
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={() => alert(`Notifying dispatch: ${police_protocol.action}`)}
          >
            <Radio size={16} />
            Apply & Notify Dispatch
          </button>
        )}
      </div>
    </div>
  );
}

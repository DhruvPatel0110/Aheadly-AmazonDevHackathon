import React, { useState } from 'react';
import { Calendar, AlertTriangle, CheckCircle, Edit3, X, Eye, Clock, ShieldCheck } from 'lucide-react';

export default function CandidateReviewCard({
  candidate,
  onConfirm,
  onEdit,
  onDismiss,
  onViewEvidence
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editDate, setEditDate] = useState(candidate.candidate_date !== 'UNVERIFIED' ? candidate.candidate_date : '');
  const [editProvider, setEditProvider] = useState(candidate.provider_name || '');
  const [leadDays, setLeadDays] = useState(candidate.category === 'insurance' ? [14, 3] : [3, 1]);

  const isUnverified = candidate.candidate_date === 'UNVERIFIED' || candidate.status === 'date_unverified';

  const handleSaveEdit = () => {
    if (!editDate) return;
    onEdit(candidate.id, {
      candidate_date: editDate,
      provider_name: editProvider,
      verification_status: 'user_confirmed',
      status: 'confirmed'
    });
    setIsEditing(false);
  };

  const handleDirectConfirm = () => {
    if (isUnverified && !editDate) {
      setIsEditing(true);
      return;
    }
    onConfirm(candidate.id, {
      confirmed_date: editDate || candidate.candidate_date,
      provider_name: editProvider || candidate.provider_name,
      lead_days: leadDays
    });
  };

  return (
    <div
      style={{
        background: '#FFFDF9',
        border: '1px solid #EBDCC8',
        borderLeft: isUnverified ? '4px solid #D97706' : '4px solid #000035',
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: 'var(--shadow-sm)'
      }}
    >
      {/* Header & Badges */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '700', margin: 0, color: '#000035' }}>
              {isEditing ? (
                <input
                  type="text"
                  className="input-cream"
                  value={editProvider}
                  onChange={(e) => setEditProvider(e.target.value)}
                  style={{ width: '180px', padding: '3px 8px', fontSize: '13px' }}
                />
              ) : (
                candidate.provider_name
              )}
            </h3>

            <span className="status-pill blue" style={{ fontSize: '10.5px', padding: '2px 8px' }}>
              {candidate.category}
            </span>
            <span style={{ fontSize: '11px', color: '#8C9A90', textTransform: 'lowercase' }}>
              {candidate.obligation_type?.replace(/_/g, ' ')}
            </span>
          </div>

          {candidate.amount !== null && candidate.amount !== undefined && (
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: '#000035', marginTop: '4px' }}>
              ₹{Number(candidate.amount).toLocaleString('en-IN')}
            </div>
          )}
        </div>

        {/* Date Display */}
        <div style={{ textAlign: 'right' }}>
          {isEditing ? (
            <input
              type="date"
              className="input-cream"
              value={editDate}
              onChange={(e) => setEditDate(e.target.value)}
              style={{ padding: '3px 6px', fontSize: '12px', width: '135px' }}
            />
          ) : isUnverified ? (
            <span className="status-pill amber">
              <span className="status-dot" />
              <span>Date Unverified</span>
            </span>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', fontWeight: '700', color: '#000035' }}>
              <Calendar size={13} color="#8C9A90" />
              <span>{candidate.candidate_date}</span>
            </div>
          )}
        </div>
      </div>

      {/* Ambiguity Alert Notice (Scenario D) */}
      {isUnverified && (
        <div
          style={{
            background: '#FDF2DE',
            border: '1px solid #F7DFB3',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11.5px',
            color: '#925700',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <AlertTriangle size={15} color="#D97706" style={{ flexShrink: 0 }} />
          <span>
            <strong>Zero-Hallucination Guard:</strong> The document did not state an explicit calendar date. Please review the evidence snippet and specify the exact due date.
          </span>
        </div>
      )}

      {/* Verbatim Evidence Snippet */}
      <div
        style={{
          background: '#FAF2E5',
          border: '1px solid #EADBCA',
          borderRadius: '8px',
          padding: '10px 12px',
          fontSize: '12px',
          color: '#374151',
          lineHeight: '1.5'
        }}
      >
        <span style={{ fontWeight: '600', color: '#000035', display: 'block', marginBottom: '2px', fontSize: '11px' }}>
          Verbatim Source Evidence:
        </span>
        “{candidate.evidence_snippet}”
      </div>

      {/* Controls & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '4px', flexWrap: 'wrap', gap: '8px' }}>
        <button
          className="btn btn-outline btn-sm"
          onClick={() => onViewEvidence(candidate)}
        >
          <Eye size={13} />
          <span>Inspect Evidence</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isEditing ? (
            <>
              <button className="btn btn-navy btn-sm" onClick={handleSaveEdit}>
                Save Changes
              </button>
              <button className="btn btn-outline btn-sm" onClick={() => setIsEditing(false)}>
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setIsEditing(true)}
                title="Edit extracted date or provider"
              >
                <Edit3 size={13} />
                <span>Edit</span>
              </button>

              <button
                className="btn btn-navy btn-sm"
                onClick={handleDirectConfirm}
                title="Confirm deadline and schedule advance alerts"
              >
                <CheckCircle size={13} />
                <span>{isUnverified ? 'Set Date' : 'Confirm Date'}</span>
              </button>

              <button
                className="btn btn-outline btn-sm"
                onClick={() => onDismiss(candidate.id)}
                title="Dismiss candidate"
                style={{ padding: '5px' }}
              >
                <X size={14} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

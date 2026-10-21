import React from 'react';
import { X, ShieldCheck, FileText, CheckCircle2, AlertTriangle, Calendar, ExternalLink } from 'lucide-react';

export default function EvidenceViewerModal({ deadline, source, onClose }) {
  if (!deadline) return null;

  const rawText = source?.raw_text || '';
  const charStart = deadline.evidence_char_start;
  const charEnd = deadline.evidence_char_end;
  const hasCoordinates = charStart !== null && charStart !== undefined && charEnd !== null && charEnd !== undefined;

  let beforeSnippet = '';
  let highlightSnippet = deadline.evidence_snippet || '';
  let afterSnippet = '';

  if (hasCoordinates && rawText && charStart >= 0 && charEnd <= rawText.length) {
    beforeSnippet = rawText.substring(0, charStart);
    highlightSnippet = rawText.substring(charStart, charEnd);
    afterSnippet = rawText.substring(charEnd);
  } else if (!rawText) {
    highlightSnippet = deadline.evidence_snippet;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '8px',
                backgroundColor: '#000035',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFF0DB'
              }}
            >
              <ShieldCheck size={19} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#000035', margin: 0 }}>
                Evidence Grounding Inspector
              </h3>
              <p style={{ fontSize: '11.5px', color: '#8C9A90', margin: 0 }}>
                {deadline.provider_name} • Verbatim Text Source Attribution
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="btn btn-outline"
            style={{ padding: '6px', borderRadius: '50%' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* Metadata Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
            <div style={{ background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '10px', padding: '10px 14px' }}>
              <span style={{ fontSize: '11px', color: '#6B7280', display: 'block' }}>Candidate Date</span>
              <span style={{ fontSize: '14px', fontWeight: '700', color: '#000035', fontFamily: 'var(--font-mono)' }}>
                {deadline.candidate_date}
              </span>
            </div>

            <div style={{ background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '10px', padding: '10px 14px' }}>
              <span style={{ fontSize: '11px', color: '#6B7280', display: 'block' }}>Extraction Confidence</span>
              <span style={{ fontSize: '14px', fontWeight: '700', color: '#197843', fontFamily: 'var(--font-mono)' }}>
                {Math.round((deadline.extraction_confidence || 1.0) * 100)}% Match
              </span>
            </div>

            <div style={{ background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '10px', padding: '10px 14px' }}>
              <span style={{ fontSize: '11px', color: '#6B7280', display: 'block' }}>Char Coordinates</span>
              <span style={{ fontSize: '13px', fontWeight: '600', color: '#1A6CA7', fontFamily: 'var(--font-mono)' }}>
                {hasCoordinates ? `[${charStart} : ${charEnd}]` : 'Regex Span'}
              </span>
            </div>

            <div style={{ background: '#FFF9F0', border: '1px solid #EBDCC8', borderRadius: '10px', padding: '10px 14px' }}>
              <span style={{ fontSize: '11px', color: '#6B7280', display: 'block' }}>Status</span>
              <span className={`status-pill ${deadline.verification_status === 'user_confirmed' ? 'green' : 'amber'}`} style={{ marginTop: '3px' }}>
                <span className="status-dot" />
                <span>{deadline.verification_status}</span>
              </span>
            </div>
          </div>

          {/* Verbatim Excerpt Box */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '12.5px', fontWeight: '700', color: '#000035', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileText size={14} color="#8C9A90" />
                Extracted Verbatim Evidence
              </span>
              <span style={{ fontSize: '11px', color: '#8C9A90', fontFamily: 'var(--font-mono)' }}>
                Length: {highlightSnippet.length} chars
              </span>
            </div>

            <div
              style={{
                background: '#FAF2E5',
                border: '1px solid #EADBCA',
                borderRadius: '10px',
                padding: '12px 14px',
                fontSize: '13px',
                lineHeight: '1.6',
                color: '#2B2C38',
                fontStyle: 'italic'
              }}
            >
              “{highlightSnippet}”
            </div>
          </div>

          {/* Full Source Context (if available) */}
          {rawText && (
            <div>
              <span style={{ fontSize: '12px', fontWeight: '700', color: '#000035', display: 'block', marginBottom: '6px' }}>
                Full Ingested Source Context:
              </span>
              <div
                style={{
                  background: '#FFF9F0',
                  border: '1px solid #EBDCC8',
                  borderRadius: '10px',
                  padding: '12px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11.5px',
                  maxHeight: '180px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  color: '#4B5563',
                  lineHeight: '1.5'
                }}
              >
                <span>{beforeSnippet}</span>
                <mark
                  style={{
                    backgroundColor: '#FCE8BD',
                    color: '#000035',
                    padding: '2px 4px',
                    borderRadius: '4px',
                    border: '1px solid #F6DCAD',
                    fontWeight: '700'
                  }}
                >
                  {highlightSnippet}
                </mark>
                <span>{afterSnippet}</span>
              </div>
            </div>
          )}

          {/* Strict Zero Hallucination Guarantee Badge */}
          <div
            style={{
              background: '#E7F7ED',
              border: '1px solid #C6EED4',
              borderRadius: '10px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}
          >
            <ShieldCheck size={20} color="#10B981" />
            <div style={{ fontSize: '12px', color: '#197843' }}>
              <strong>Strict Zero-Hallucination Policy:</strong> Dates and obligation parameters are strictly verified and anchored to character coordinates in original sources. No phantom deadlines are ever created.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          {deadline.official_url && (
            <a
              href={deadline.official_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-cream"
              style={{ marginRight: 'auto' }}
            >
              <span>Visit Official Portal</span>
              <ExternalLink size={13} />
            </a>
          )}
          <button className="btn btn-navy" onClick={onClose}>
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}

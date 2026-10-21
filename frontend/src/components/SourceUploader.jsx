import React, { useState } from 'react';
import { UploadCloud, FileText, Send, Sparkles, AlertCircle, CheckCircle2, FileCheck } from 'lucide-react';

const DEMO_SCENARIOS = [
  {
    id: 'scenario_a',
    title: 'Scenario A: Netflix Free Trial',
    badge: 'Subscription',
    snippet: `From: info@mailer.netflix.com
Subject: Your free trial is coming to an end

Dear Member,
Your 14-day free trial ends on October 20 2026. Your card will be charged ₹499/month unless cancelled 24 hours prior. Manage your membership anytime in Account Settings.`,
    desc: 'Tests trial_ending extraction, ₹499 amount, and cancellation guide.'
  },
  {
    id: 'scenario_b',
    title: 'Scenario B: HDFC Insurance Premium',
    badge: 'Insurance',
    snippet: `From: renewals@hdfcergo.com
Subject: Renewal Notice for Policy HDFC-98213

Dear Policyholder,
Policy No: HDFC-98213. Your annual premium of ₹14,250 is due on November 05, 2026 to ensure continuous coverage. Please pay before the due date to avoid policy lapse.`,
    desc: 'Tests ₹14,250 parsing, DD-Month format, and 14-day advance reminders.'
  },
  {
    id: 'scenario_c',
    title: 'Scenario C: Broadband & Utility Bills',
    badge: 'Household Bills',
    snippet: `From: ebill@airtel.com
Subject: Airtel Fiber Bill Notification

Dear Customer,
Your Airtel Wi-Fi bill for Account 080234567 is due on 2026-11-15 for INR 999. Valid till 25-Nov to avoid disconnection. Pay online via Airtel Thanks app.`,
    desc: 'Tests multiple dates, chronological aggregation, and provider links.'
  },
  {
    id: 'scenario_d',
    title: 'Scenario D: Vague Ambiguity',
    badge: 'Integrity Check',
    snippet: `Subject: Maintenance Fee Reminder
Notice:
Hi Dhruv, your annual maintenance fee will be due sometime near the end of the month. Please keep funds ready.`,
    desc: 'Strictly refuses to invent dates. Flags as date_unverified.'
  }
];

export default function SourceUploader({ onSourceIngested, isLoading }) {
  const [activeTab, setActiveTab] = useState('scenarios'); // 'scenarios' | 'text' | 'file'
  const [textInput, setTextInput] = useState('');
  const [titleInput, setTitleInput] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSelectScenario = (scenario) => {
    setTextInput(scenario.snippet);
    setTitleInput(scenario.title);
    setErrorMsg('');
    setSuccessMsg(`Preloaded ${scenario.title}. Click "Ingest & Extract" below.`);
  };

  const handleTextSubmit = async (e) => {
    e?.preventDefault();
    if (!textInput.trim()) {
      setErrorMsg('Please enter or paste document text.');
      return;
    }
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const formData = new FormData();
      formData.append('raw_text', textInput);
      formData.append('title', titleInput.trim() || 'Pasted Source Document');

      const res = await fetch('/api/sources/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to ingest source.');
      }

      setSuccessMsg(`Successfully ingested "${data.source.title}"! Identified ${data.candidates?.length || 0} candidate(s).`);
      if (onSourceIngested) onSourceIngested(data);
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0] || selectedFile;
    if (!file) {
      setErrorMsg('Please select a file (.txt, .eml, or digital .pdf).');
      return;
    }

    setErrorMsg('');
    setSuccessMsg('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (titleInput.trim()) {
        formData.append('title', titleInput.trim());
      }

      const res = await fetch('/api/sources/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to upload and parse file.');
      }

      setSuccessMsg(`File "${file.name}" ingested! Extracted ${data.candidates?.length || 0} candidate(s).`);
      setSelectedFile(null);
      if (onSourceIngested) onSourceIngested(data);
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Sub-tab selection */}
      <div style={{ display: 'flex', gap: '6px', background: 'rgba(0, 0, 53, 0.04)', padding: '3px', borderRadius: 'var(--radius-full)' }}>
        {[
          { key: 'scenarios', label: '1-Click Scenarios' },
          { key: 'text', label: 'Paste Text / Email' },
          { key: 'file', label: 'Upload File' }
        ].map((tab) => (
          <button
            key={tab.key}
            className={`filter-pill ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => { setActiveTab(tab.key); setErrorMsg(''); }}
            style={{ flex: 1, textAlign: 'center' }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Alerts */}
      {errorMsg && (
        <div style={{ background: '#FEEBEB', border: '1px solid #FCD0D0', borderRadius: '10px', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '8px', color: '#C52222', fontSize: '12px' }}>
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div style={{ background: '#E7F7ED', border: '1px solid #C6EED4', borderRadius: '10px', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '8px', color: '#197843', fontSize: '12px' }}>
          <CheckCircle2 size={16} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Tab 1: Demo Scenarios */}
      {activeTab === 'scenarios' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ fontSize: '12px', color: '#6B7280' }}>
            Choose a benchmark scenario from the hackathon test suite:
          </div>
          {DEMO_SCENARIOS.map((sc) => (
            <div
              key={sc.id}
              onClick={() => handleSelectScenario(sc)}
              style={{
                background: '#FFFDF9',
                border: '1px solid #EBDCC8',
                borderRadius: '12px',
                padding: '12px 14px',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              className="stat-card"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '13px', fontWeight: '700', color: '#000035' }}>
                  {sc.title}
                </span>
                <span className="status-pill blue" style={{ fontSize: '10.5px', padding: '2px 8px' }}>
                  {sc.badge}
                </span>
              </div>
              <p style={{ fontSize: '11.5px', color: '#6B7280', margin: 0 }}>
                {sc.desc}
              </p>
            </div>
          ))}

          {textInput && (
            <div style={{ marginTop: '6px' }}>
              <button
                className="btn btn-navy"
                onClick={handleTextSubmit}
                disabled={isLoading}
                style={{ width: '100%', padding: '10px' }}
              >
                <Sparkles size={14} />
                <span>Ingest & Extract Obligations</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Direct Text Paste */}
      {activeTab === 'text' && (
        <form onSubmit={handleTextSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div>
            <label style={{ fontSize: '11.5px', fontWeight: '600', color: '#000035', display: 'block', marginBottom: '4px' }}>
              Document Title (Optional)
            </label>
            <input
              type="text"
              className="input-cream"
              placeholder="e.g., Netflix Renewal Email"
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
            />
          </div>

          <div>
            <label style={{ fontSize: '11.5px', fontWeight: '600', color: '#000035', display: 'block', marginBottom: '4px' }}>
              Document / Email Content
            </label>
            <textarea
              className="input-cream"
              style={{ minHeight: '120px', resize: 'vertical' }}
              placeholder="Paste raw email body, notice text, or SMS snippet..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn btn-navy"
            disabled={isLoading || !textInput.trim()}
            style={{ width: '100%', padding: '10px' }}
          >
            <Send size={14} />
            <span>Parse & Extract Candidates</span>
          </button>
        </form>
      )}

      {/* Tab 3: File Upload */}
      {activeTab === 'file' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div
            style={{
              border: '2px dashed #D3CEBF',
              borderRadius: '14px',
              padding: '24px 16px',
              textAlign: 'center',
              backgroundColor: '#FFFBF5',
              cursor: 'pointer'
            }}
            onClick={() => document.getElementById('file-upload-input')?.click()}
          >
            <UploadCloud size={32} color="#8C9A90" style={{ margin: '0 auto 8px' }} />
            <p style={{ fontSize: '13px', fontWeight: '600', color: '#000035', margin: '0 0 4px' }}>
              Click to browse or drop document
            </p>
            <p style={{ fontSize: '11.5px', color: '#8C9A90', margin: 0 }}>
              Supports .txt, .eml, and digital .pdf (₹0 local parsing)
            </p>
            <input
              id="file-upload-input"
              type="file"
              accept=".txt,.eml,.pdf,message/rfc822,text/plain,application/pdf"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
          </div>

          <div style={{ fontSize: '11px', color: '#8C9A90', textAlign: 'center' }}>
            🔒 Local-First: All parsing executes strictly on your local machine with zero external cloud API dependencies.
          </div>
        </div>
      )}
    </div>
  );
}

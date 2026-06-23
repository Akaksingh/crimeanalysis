import React, { useEffect, useState } from 'react';
import { api } from './api.js';

// red for positive, blue for negative; intensity by |r|. Significant cells are bold.
function cellColor(r) {
  const a = Math.min(Math.abs(r), 1);
  const alpha = 0.12 + a * 0.6;
  return r >= 0 ? `rgba(210,59,59,${alpha})` : `rgba(95,176,255,${alpha})`;
}
const VERDICT_TAG = {
  confirmed: { t: '✓ confirms theory', c: '#1ea672' },
  contradicted: { t: '✗ contradicts theory', c: '#e8730c' },
  inconclusive: { t: 'not significant', c: '#6b7c93' },
  exploratory: { t: 'exploratory', c: '#9aa7bf' },
};

export default function Correlations() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    api.seCorrelations().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="error">Socio-economic API error: {err}</div>;
  if (!data) return <p className="hint">Loading correlations…</p>;

  const indicators = [...new Set(data.matrix.map((m) => m.indicator))];
  const groups = [...new Set(data.matrix.map((m) => m.crime_group))];
  const lookup = {};
  data.matrix.forEach((m) => { lookup[`${m.indicator}|${m.crime_group}`] = m; });

  return (
    <div>
      <div className="synthetic-tag">
        Ecological (district-level) correlations · Census 2011 socio-economic × NCRB crime rates ({data.crime_year}) ·
        n={data.n_districts}. Correlation ≠ causation; recorded crime reflects reporting. Not for profiling individuals or communities.
      </div>

      <section className="panel">
        <h2>Socio-economic ↔ crime correlation matrix</h2>
        <p className="hint">Pearson r per district. <span style={{ color: '#d23b3b' }}>red = positive</span>,
          <span style={{ color: '#5fb0ff' }}> blue = negative</span>; <b>bold</b> = significant (p&lt;0.05). Hover a cell.</p>
        <div className="scroll" style={{ overflowX: 'auto' }}>
          <table className="matrix">
            <thead>
              <tr><th>Indicator \ Crime group</th>{groups.map((g) => <th key={g}>{g}</th>)}</tr>
            </thead>
            <tbody>
              {indicators.map((ind) => (
                <tr key={ind}>
                  <td className="ind">{ind.replace(/_/g, ' ')}</td>
                  {groups.map((g) => {
                    const m = lookup[`${ind}|${g}`];
                    if (!m) return <td key={g} className="empty">·</td>;
                    return (
                      <td
                        key={g}
                        style={{ background: cellColor(m.pearson_r), fontWeight: m.significant ? 700 : 400 }}
                        onMouseEnter={() => setHover(m)}
                        title={`${ind} ~ ${g}`}
                      >
                        {m.pearson_r > 0 ? '+' : ''}{m.pearson_r.toFixed(2)}{m.ethics_flag ? '⚠' : ''}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {hover && (
          <div className="hover-card">
            <b>{hover.indicator.replace(/_/g, ' ')} ~ {hover.crime_group}</b>
            <div>Pearson r = {hover.pearson_r} (p={hover.pearson_p}) · Spearman r = {hover.spearman_r} · {hover.strength}, n={hover.n}</div>
            {hover.theory && <div className="muted small">Hypothesis ({hover.hypothesized_sign}): {hover.theory}</div>}
            <span className="vtag" style={{ color: (VERDICT_TAG[hover.verdict] || {}).c }}>
              {(VERDICT_TAG[hover.verdict] || {}).t}
            </span>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Key findings <span className="year">(significant, strongest first)</span></h2>
        <table>
          <thead><tr><th>Pattern</th><th>r</th><th>p</th><th>Strength</th><th>Verdict</th></tr></thead>
          <tbody>
            {data.key_findings.map((c, i) => (
              <tr key={i}>
                <td>{c.indicator.replace(/_/g, ' ')} → <b>{c.crime_group}</b>{c.ethics_flag ? ' ⚠' : ''}</td>
                <td style={{ color: c.pearson_r >= 0 ? '#ff6b6b' : '#5fb0ff' }}>{c.pearson_r > 0 ? '+' : ''}{c.pearson_r}</td>
                <td>{c.pearson_p}</td>
                <td>{c.strength}</td>
                <td style={{ color: (VERDICT_TAG[c.verdict] || {}).c }}>{(VERDICT_TAG[c.verdict] || {}).t}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small" style={{ marginTop: 10 }}>
          ⚠ marks protected-attribute indicators (SC/ST share, sex ratio) — included only to explain
          victimization/reporting, never offending. Interpret with human review.
        </p>
      </section>
    </div>
  );
}

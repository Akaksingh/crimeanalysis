import React, { useEffect, useState } from 'react';
import { api } from './api.js';
import CrimeMap from './CrimeMap.jsx';
import Intelligence from './Intelligence.jsx';
import Correlations from './Correlations.jsx';

const BAND_COLOR = { Low: '#1ea672', Medium: '#d8a300', High: '#e8730c', Critical: '#d23b3b' };
const STATUS_LABEL = { none: '—', emerging: 'Emerging', established: 'Hotspot' };

export default function App() {
  const [meta, setMeta] = useState(null);
  const [districts, setDistricts] = useState([]);
  const [boundaries, setBoundaries] = useState(null);
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState('overview'); // 'overview' | 'intelligence'
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.meta(),
      api.districts(),
      fetch('/data/karnataka_districts.geojson').then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([m, d, b]) => { setMeta(m); setDistricts(d); setBoundaries(b); })
      .catch((e) => setError(e.message));
  }, []);

  const select = (id) => api.district(id).then(setSelected).catch((e) => setError(e.message));

  if (error) {
    return (
      <div className="wrap">
        <h1>AI-Driven Crime Analytics</h1>
        <div className="error">
          Could not reach the API ({error}).<br />
          Start the backend: <code>python -m pipeline.run</code> then
          <code>uvicorn app.main:app --reload</code>.
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <header>
        <h1>AI-Driven Crime Analytics <span className="pill">Karnataka</span></h1>
        {meta && (
          <p className="sub">
            {meta.district_count} districts · {meta.years[0]}–{meta.years[meta.years.length - 1]} ·
            latest {meta.latest_year} · <span className="tag">{meta.data_note}</span>
          </p>
        )}
        <nav className="tabs">
          <button className={tab === 'overview' ? 'on' : ''} onClick={() => setTab('overview')}>Map & Districts</button>
          <button className={tab === 'intelligence' ? 'on' : ''} onClick={() => setTab('intelligence')}>Intelligence</button>
          <button className={tab === 'correlations' ? 'on' : ''} onClick={() => setTab('correlations')}>Socio-economic</button>
        </nav>
      </header>

      {tab === 'intelligence' ? (
        <Intelligence />
      ) : tab === 'correlations' ? (
        <Correlations />
      ) : (
        <>
          {districts.length > 0 && (
            <CrimeMap
              districts={districts}
              boundaries={boundaries}
              selectedId={selected?.geo_unit_id}
              onSelect={select}
            />
          )}
          <OverviewCols districts={districts} selected={selected} select={select} />
        </>
      )}
    </div>
  );
}

function OverviewCols({ districts, selected, select }) {
  return (
      <div className="cols">
        <section className="panel">
          <h2>Districts by risk</h2>
          <div className="scroll">
            <table>
              <thead>
                <tr><th>District</th><th>Rate/100k</th><th>Hotspot</th><th>Risk</th></tr>
              </thead>
              <tbody>
                {districts.map((d) => (
                  <tr
                    key={d.geo_unit_id}
                    className={selected?.geo_unit_id === d.geo_unit_id ? 'sel' : ''}
                    onClick={() => select(d.geo_unit_id)}
                  >
                    <td>{d.name}</td>
                    <td>{d.crime_rate_per_100k}</td>
                    <td>{STATUS_LABEL[d.hotspot_status]}</td>
                    <td><span className="band" style={{ background: BAND_COLOR[d.risk_band] }}>{d.risk_band} {d.risk_score}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          {!selected ? <p className="hint">Select a district on the map or table to drill down.</p> : <DistrictDetail d={selected} />}
        </section>
      </div>
  );
}

function DistrictDetail({ d }) {
  const maxTotal = Math.max(...d.trend.map((t) => t.total), 1);
  const maxCat = Math.max(...d.breakdown.map((b) => b.cases), 1);
  return (
    <div>
      <h2>{d.name} <span className="year">({d.year})</span></h2>
      <div className="kpis">
        <Kpi label="Cognizable cases" value={d.kpis.total_cognizable_cases.toLocaleString()} />
        <Kpi label="Rate / 100k" value={d.kpis.crime_rate_per_100k} />
        <Kpi label="Severity index" value={d.kpis.severity_weighted_index} />
        <Kpi label="Violent share" value={`${(d.kpis.violent_crime_share * 100).toFixed(1)}%`} />
      </div>

      <h3>Risk <span className="band" style={{ background: BAND_COLOR[d.risk.band] }}>{d.risk.band} {d.risk.score}</span>
        {d.risk.partial && <em className="note"> partial — open data only</em>}
      </h3>
      <ul className="components">
        {Object.entries(d.risk.components).map(([k, c]) => (
          <li key={k}><span>{k.replace(/_/g, ' ')}</span> <b>+{c.contribution}</b></li>
        ))}
      </ul>

      <h3>Trend ({d.trend[0].year}–{d.trend[d.trend.length - 1].year})</h3>
      <div className="bars">
        {d.trend.map((t) => (
          <div key={t.year} className="bar-row">
            <span className="bar-label">{t.year}</span>
            <div className="bar" style={{ width: `${(t.total / maxTotal) * 100}%` }} />
            <span className="bar-val">{t.total.toLocaleString()}</span>
          </div>
        ))}
      </div>

      <h3>Top categories</h3>
      <div className="bars">
        {d.breakdown.slice(0, 8).map((b) => (
          <div key={b.category_code} className="bar-row">
            <span className="bar-label">{b.category_code}</span>
            <div className="bar cat" style={{ width: `${(b.cases / maxCat) * 100}%` }} />
            <span className="bar-val">{b.cases.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const Kpi = ({ label, value }) => (
  <div className="kpi"><div className="kpi-val">{value}</div><div className="kpi-label">{label}</div></div>
);

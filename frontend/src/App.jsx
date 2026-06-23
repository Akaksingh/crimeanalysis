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

  const NAV = [
    { id: 'overview', label: 'Map & Districts' },
    { id: 'intelligence', label: 'Crime Intelligence' },
    { id: 'correlations', label: 'Socio-economic' },
  ];

  return (
    <Shell meta={meta} tab={tab} setTab={setTab} nav={NAV}>
      {error ? (
        <div className="error">
          Could not reach the API ({error}).<br />
          Start the backend: <code>python -m pipeline.run</code> then
          <code>uvicorn app.main:app --reload</code>.
        </div>
      ) : tab === 'intelligence' ? (
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
    </Shell>
  );
}

// Government-of-Karnataka / Karnataka State Police chrome: utility bar, tricolor
// strip, emblem + bilingual title, primary navigation, and an official footer.
function Shell({ meta, tab, setTab, nav, children }) {
  const active = nav.find((n) => n.id === tab)?.label ?? '';
  return (
    <>
      <a className="skip-link" href="#main">Skip to main content</a>

      <div className="gov-topbar">
        <div className="gov-topbar-in">
          <span className="gov-india">Government of Karnataka · ಕರ್ನಾಟಕ ಸರ್ಕಾರ</span>
          <div className="gov-top-actions">
            <button type="button" aria-label="Decrease text size">A-</button>
            <button type="button" aria-label="Default text size">A</button>
            <button type="button" aria-label="Increase text size">A+</button>
            <span className="sep" />
            <a className="on" href="#" aria-current="true">English</a>
            <a href="#" lang="kn">ಕನ್ನಡ</a>
            <span className="sep" />
            <a href="#">Sign In</a>
          </div>
        </div>
      </div>

      <div className="tricolor" aria-hidden="true" />

      <header className="gov-header">
        <div className="gov-header-in">
          <img
            className="gov-emblem"
            src="/ksp-logo.svg"
            alt="Karnataka State Police emblem"
            width="68"
            height="68"
          />
          <div className="gov-title">
            <h1>Karnataka State Police</h1>
            <div className="gov-sub-kn" lang="kn">ಕರ್ನಾಟಕ ರಾಜ್ಯ ಪೊಲೀಸ್</div>
            <div className="gov-sub-en">Government of Karnataka</div>
          </div>
          <div className="gov-portal-badge">
            <div className="gpb-kicker">Official Portal</div>
            <div className="gpb-title">Crime Analytics &amp; Intelligence Platform</div>
            <div className="gpb-sub">Data-driven policing · Pilot: Karnataka</div>
          </div>
        </div>
      </header>

      <nav className="gov-nav" aria-label="Primary">
        <div className="gov-nav-in">
          {nav.map((n) => (
            <button
              key={n.id}
              className={tab === n.id ? 'on' : ''}
              onClick={() => setTab(n.id)}
              aria-current={tab === n.id ? 'page' : undefined}
            >
              {n.label}
            </button>
          ))}
        </div>
      </nav>

      <div className="gov-context">
        <div className="gov-context-in">
          <span className="crumb">Home <span className="crumb-sep">›</span> {active}</span>
          {meta && (
            <span className="ctx-meta">
              {meta.district_count} districts · {meta.years[0]}–{meta.years[meta.years.length - 1]} ·
              latest {meta.latest_year}
            </span>
          )}
        </div>
      </div>

      <main id="main" className="wrap">
        {meta && (
          <div className="data-note">
            <b>Data note:</b> {meta.data_note}
          </div>
        )}
        {children}
      </main>

      <GovFooter />
    </>
  );
}

function GovFooter() {
  return (
    <footer className="gov-footer">
      <div className="gov-footer-in">
        <div className="gf-col">
          <h4>Karnataka State Police</h4>
          <p className="gf-text">
            Crime Analytics &amp; Intelligence Platform — a decision-support tool
            for data-driven policing across Karnataka districts.
          </p>
          <p className="gf-text gf-warn">
            ⚠ Person-level offender &amp; network data shown here is synthetic
            (no open person-level crime data exists) and anchored to real district
            crime volumes. District crime figures are real (NCRB).
          </p>
        </div>
        <div className="gf-col">
          <h4>Website Policies</h4>
          <ul className="gf-links">
            <li><a href="#">Copyright Policy</a></li>
            <li><a href="#">Hyperlinking Policy</a></li>
            <li><a href="#">Terms &amp; Conditions</a></li>
            <li><a href="#">Privacy Policy</a></li>
            <li><a href="#">Accessibility Statement</a></li>
          </ul>
        </div>
        <div className="gf-col">
          <h4>Related Links</h4>
          <ul className="gf-links">
            <li><a href="https://karnataka.gov.in" target="_blank" rel="noreferrer">Government of Karnataka</a></li>
            <li><a href="https://ksp.karnataka.gov.in" target="_blank" rel="noreferrer">Karnataka State Police</a></li>
            <li><a href="https://ncrb.gov.in" target="_blank" rel="noreferrer">NCRB</a></li>
            <li><a href="https://www.india.gov.in" target="_blank" rel="noreferrer">India.gov.in</a></li>
            <li><a href="https://www.digitalindia.gov.in" target="_blank" rel="noreferrer">Digital India</a></li>
          </ul>
        </div>
        <div className="gf-col">
          <h4>Help &amp; Emergency</h4>
          <ul className="gf-links">
            <li>Police Control Room: <b>100</b></li>
            <li>Emergency Response: <b>112</b></li>
            <li>Women Helpline: <b>1091</b></li>
            <li>Cyber Crime: <b>1930</b></li>
          </ul>
        </div>
      </div>
      <div className="gov-footer-bar">
        <span>
          © {new Date().getFullYear()} Karnataka State Police, Government of Karnataka.
          Content owned and maintained by Karnataka State Police.
        </span>
        <span>Best viewed in modern browsers · Built for the AI-Driven Crime Analytics pilot</span>
      </div>
    </footer>
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

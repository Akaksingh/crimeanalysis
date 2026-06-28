// Thin API client for the Phase 1 aggregate API.
// In dev, Vite proxies /api -> FastAPI (see vite.config.js). Override with
// VITE_API_BASE for a deployed backend.
const BASE = import.meta.env.VITE_API_BASE || '';

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  meta: () => get('/api/meta'),
  districts: () => get('/api/districts'),
  district: (id) => get(`/api/districts/${encodeURIComponent(id)}`),
  hotspots: () => get('/api/hotspots'),
  trends: () => get('/api/trends'),
  intelRepeat: () => get('/api/intelligence/repeat-offenders'),
  intelNetwork: () => get('/api/intelligence/network'),
  intelPatterns: () => get('/api/intelligence/patterns'),
  seIndicators: () => get('/api/socioeconomic'),
  seCorrelations: () => get('/api/socioeconomic/correlations'),
  // Phase 7 — FIR-record intelligence (KSP Police FIR System schema)
  firOverview: () => get('/api/fir/overview'),
  firStations: () => get('/api/fir/stations'),
  firSpatiotemporal: () => get('/api/fir/spatiotemporal'),
  firNetwork: () => get('/api/fir/network'),
  firOffenders: () => get('/api/fir/offenders'),
  firCases: () => get('/api/fir/cases'),
  firSchema: () => get('/api/fir/schema'),
};

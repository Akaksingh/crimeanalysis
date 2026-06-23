import React, { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';

// Vivid palette to distinguish co-offending clusters (component id -> color).
// Netflix red leads; the rest give enough separation for many components.
const PALETTE = [
  '#e50914', '#ff6a70', '#f5b301', '#4f9dff', '#7c5cff',
  '#1ec98b', '#ff8a3d', '#d36bff', '#36c5d8', '#c0c0c0',
];
const colorFor = (component) => PALETTE[component % PALETTE.length];

// Interactive 3D co-offending network — drag to rotate 360°, scroll to zoom,
// drag a node to reposition, click a node to inspect. Opens in a modal overlay.
export default function NetworkGraph({ graph, summary, onClose }) {
  const fgRef = useRef();
  const boxRef = useRef();
  const [dims, setDims] = useState({ w: 800, h: 520 });
  const [selected, setSelected] = useState(null);
  const [focusLargest, setFocusLargest] = useState(false);

  // size the canvas to its container
  useEffect(() => {
    if (!boxRef.current) return;
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect;
      setDims({ w: Math.max(320, width), h: Math.max(360, height) });
    });
    ro.observe(boxRef.current);
    return () => ro.disconnect();
  }, []);

  // close on Escape
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const data = useMemo(() => {
    if (!focusLargest) return graph;
    const nodes = graph.nodes.filter((n) => n.component === 0); // 0 = largest
    const ids = new Set(nodes.map((n) => n.id));
    const links = graph.links.filter(
      (l) => ids.has(l.source.id ?? l.source) && ids.has(l.target.id ?? l.target),
    );
    return { nodes, links };
  }, [graph, focusLargest]);

  const focusNode = (node) => {
    setSelected(node);
    const fg = fgRef.current;
    if (!fg || node.x == null) return;
    const dist = 70;
    const ratio = 1 + dist / Math.hypot(node.x, node.y, node.z || 1);
    fg.cameraPosition(
      { x: node.x * ratio, y: node.y * ratio, z: node.z * ratio },
      node,
      1200,
    );
  };

  return (
    <div className="graph-modal" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="graph-dialog">
        <div className="graph-head">
          <div>
            <h2>Co-offending Network Graph</h2>
            <div className="muted small">
              {data.nodes.length} offenders · {data.links.length} co-offence links ·
              {' '}{summary.components} clusters — drag to rotate · scroll to zoom · click a node
            </div>
          </div>
          <div className="graph-actions">
            <button
              className={focusLargest ? 'on' : ''}
              onClick={() => { setFocusLargest((v) => !v); setSelected(null); }}
            >
              {focusLargest ? 'Show all clusters' : 'Focus largest cluster'}
            </button>
            <button className="graph-close" onClick={onClose} aria-label="Close">✕</button>
          </div>
        </div>

        <div className="graph-canvas" ref={boxRef}>
          <ForceGraph3D
            ref={fgRef}
            width={dims.w}
            height={dims.h}
            graphData={data}
            backgroundColor="#0b0b0b"
            showNavInfo={false}
            nodeRelSize={4}
            nodeVal={(n) => 1 + n.degree}
            nodeColor={(n) => (selected && n.id === selected.id ? '#ffffff' : colorFor(n.component))}
            nodeOpacity={0.92}
            nodeLabel={(n) =>
              `<div style="font:600 12px Inter,sans-serif;color:#fff;background:#181818;
                 border:1px solid #383838;border-radius:6px;padding:6px 9px">
                 ${n.name} &middot; <span style="color:#8c8c8c">${n.district ?? '—'}</span><br/>
                 <span style="color:#ff6a70">${n.degree} co-offenders</span> &middot;
                 ${n.incidents} cases</div>`}
            linkColor={() => 'rgba(229,9,20,0.45)'}
            linkOpacity={0.5}
            linkWidth={(l) => 0.4 + (l.weight || 1) * 0.5}
            linkDirectionalParticles={1}
            linkDirectionalParticleWidth={1.6}
            linkDirectionalParticleColor={() => '#ff6a70'}
            onNodeClick={focusNode}
            onBackgroundClick={() => setSelected(null)}
          />

          {selected && (
            <div className="graph-detail">
              <button className="graph-close" onClick={() => setSelected(null)} aria-label="Close details">✕</button>
              <div className="gd-name">{selected.name}</div>
              <div className="gd-row"><span>District</span><b>{selected.district ?? '—'}</b></div>
              <div className="gd-row"><span>Co-offenders</span><b>{selected.degree}</b></div>
              <div className="gd-row"><span>Cases</span><b>{selected.incidents}</b></div>
              <div className="gd-row"><span>Cluster</span><b>#{selected.component}</b></div>
              <div className="muted small" style={{ marginTop: 8 }}>
                Synthetic entity · ID {selected.id}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

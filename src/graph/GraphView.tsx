// Atlas graph: one React Flow engine, two modes.
//   Overview (no focus): objectives -> technique families, "+N" expands a family's attacks.
//   Focus: one card with its neighbours grouped by relation in rank bands.
// Interaction model (same on every viewport, so it stays predictable):
//   click / Space on a card  -> re-focus inside the graph only (trail updates here,
//                               the reader and URL stay put; mobile stays on the graph);
//   "Open" button / Enter    -> re-focus here too, then load the node in the reader and push /nodes/<id>/.
// When the reader navigates (focusId prop or focusNonce change), the graph follows it
// and its trail restarts from that node.
// Keyboard: the canvas is one tab stop (roving tabindex); arrow keys move between cards.
// The relation-group chips are one tab stop too (arrow keys move along the row).

import '@xyflow/react/dist/base.css';
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { ReactFlow, ReactFlowProvider, MiniMap, useReactFlow, useStore } from '@xyflow/react';
import {
  ZoomIn, ZoomOut, LocateFixed, Maximize2, Minimize2, Network, List as ListIcon, ChevronRight, Info, X, ArrowDown, ArrowUp, ArrowLeft, ArrowRight,
} from 'lucide-react';
import { type Atlas, glyphFor } from '../atlas';
import { buildOverview, buildFocus, EDGE_CLASSES, GUTTER, CARD_W, type GraphNode, type GraphEdge, type GraphLayout, type GroupData, type SummaryData } from './layout';
import {
  CardNode, SummaryNode, GroupNode, GroupHead, ColHeadNode, AtlasEdge, EdgeSample, EvMark, GraphContext, TabStopContext, EVIDENCE, COUNT_ICONS, type GraphCtx,
} from './CardNode';

const nodeTypes = { card: CardNode, summary: SummaryNode, relgroup: GroupNode, colhead: ColHeadNode };
const edgeTypes = { atlas: AtlasEdge };
// The trail (top) and the toolbar (bottom) are strips outside the canvas, so the
// canvas only needs a small inner margin when fitting.
const PAD = { desk: 16, compact: 8 };
// Below this zoom the 15px titles drop under 12px on screen: frame part of the
// graph at a readable zoom instead, with "more" cues at the clipped edges.
const MIN_READABLE = 0.8;
const TRAIL_MAX = 10;
const ARIA_CONFIG = { 'node.a11yDescription.default': '', 'node.a11yDescription.keyboardDisabled': '', 'edge.a11yDescription.default': '' };
const PRO = { hideAttribution: true };  // MIT licence; React Flow is credited in the README

const reducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const motion = (ms: number) => (reducedMotion() ? 0 : ms);
const isCard = (n: GraphNode) => n.type === 'card' || n.type === 'summary';
const FOCUS_TAG = 24;  // the "Focus" tag drawn above the focus card (CSS ::before)
const FIT_MS = 280;

const LEGEND_KEY = 'atlas-graph-legend';
const readLegendPref = () => { try { return localStorage.getItem(LEGEND_KEY); } catch { return null; } };
const writeLegendPref = (v: boolean) => { try { localStorage.setItem(LEGEND_KEY, v ? '1' : '0'); } catch { /* private mode */ } };

interface Props {
  atlas: Atlas;
  focusId: string | null;
  focusNonce?: number;           // bump to re-sync the graph to focusId ("Focus in graph")
  onOpen: (id: string) => void;
  onList?: (id: string) => void; // reader Relationships tab: the text alternative
  full?: boolean;
  onToggleFull?: () => void;
  theme: 'light' | 'dark';
  compact?: boolean;             // mobile: tighter margins, no minimap
}

export function GraphView(props: Props) {
  return <ReactFlowProvider><GraphInner {...props} /></ReactFlowProvider>;
}
export default GraphView;

// Everything drawn: cards and boxes, the focus card's tag, and the connector lanes.
function bounds({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const pts = edges.flatMap(e => e.data?.points || []);
  const top = (n: GraphNode) => n.position.y - ((n.data as any).focus ? FOCUS_TAG : 0);
  const minX = Math.min(...nodes.map(n => n.position.x), ...pts.map(p => p.x));
  const minY = Math.min(...nodes.map(top), ...pts.map(p => p.y));
  const maxX = Math.max(...nodes.map(n => n.position.x + (n.width || 0)), ...pts.map(p => p.x));
  const maxY = Math.max(...nodes.map(n => n.position.y + (n.height || 0)), ...pts.map(p => p.y));
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY };
}

function GraphInner({ atlas, focusId, focusNonce, onOpen, onList, full, onToggleFull, theme, compact }: Props) {
  const rf = useReactFlow();
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [focus, setFocus] = useState<string | null>(focusId);
  const [trail, setTrail] = useState<string[]>(focusId ? [focusId] : []);
  const [families, setFamilies] = useState<Set<string>>(() => new Set());
  const [groups, setGroups] = useState<Set<string>>(() => new Set());
  const [hot, setHot] = useState<string | null>(null);
  const [tabStop, setTabStop] = useState<string | null>(null);
  // Legend starts closed (open, it covers part of the canvas), then remembers the viewer's choice.
  const [legendOpen, setLegendOpen] = useState(() => readLegendPref() === '1');
  const [trailAll, setTrailAll] = useState(false);  // "…" in the trail expands the hidden crumbs
  const reveal = useRef<{ id: string; frac: number } | null>(null);  // after an expand/collapse: bring this card into view
  const pendingFocus = useRef<string | null>(null);  // after a re-layout: move keyboard focus here
  const focusRef = useRef(focus);
  focusRef.current = focus;
  const onOpenRef = useRef(onOpen);
  onOpenRef.current = onOpen;
  const pad = compact ? PAD.compact : PAD.desk;

  // In-graph navigation: extends the trail (capped).
  const select = useCallback((id: string | null) => {
    if (id === focusRef.current) { setTabStop(id); return; }  // already there: keep expanded groups and the view
    setFocus(id);
    setGroups(new Set());
    setTrail(t => (id ? (t[t.length - 1] === id ? t : [...t.filter(x => x !== id), id].slice(-TRAIL_MAX)) : []));
    setTabStop(id);
    pendingFocus.current = id || '';
  }, []);

  // Follow the reader: restart the trail from its node (unless the graph is already there,
  // as after "Open", which keeps the in-graph path).
  useEffect(() => {
    const id = focusId && atlas.nodes[focusId] ? focusId : null;
    if (id === focusRef.current) return;
    setFocus(id); setGroups(new Set()); setTrail(id ? [id] : []); setTabStop(id);
  }, [focusId, focusNonce, atlas]);
  // "Focus in graph" (an explicit request, unlike reader navigation) also moves keyboard focus
  // to the focus card, so keyboard and screen-reader users land in the graph.
  useEffect(() => {
    if (!focusNonce || !focusId) return;
    let tries = 0, raf = 0;
    const go = () => {
      const el = cardEl(focusId);
      if (el) { setTabStop(focusId); el.focus({ preventScroll: true }); }
      else if (tries++ < 30) raf = requestAnimationFrame(go);
    };
    raf = requestAnimationFrame(go);
    return () => cancelAnimationFrame(raf);
  }, [focusNonce]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Canvas size: picks how many card columns a relation group gets and triggers a re-fit.
  const [size, setSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize(prev => {
      const w = el.clientWidth, h = el.clientHeight;
      if (w === prev.w && h === prev.h) return prev;
      // phones: ignore small height changes from the browser toolbar showing/hiding
      return compact && w === prev.w && Math.abs(h - prev.h) < 100 ? prev : { w, h };
    }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [compact]);
  const viewW = Math.max(0, size.w - 2 * pad), viewH = Math.max(0, size.h - 2 * pad);
  // Wider edge gutter when both overview columns still fit at a readable zoom.
  const gutter = viewW >= (2 * CARD_W + GUTTER.wide) * 0.88 ? GUTTER.wide : GUTTER.narrow;

  const layout: GraphLayout = useMemo(
    () => (focus ? buildFocus(atlas, focus, groups, { w: viewW, h: viewH }) : buildOverview(atlas, families, gutter)),
    [atlas, focus, groups, families, viewW, viewH, gutter],
  );
  const cards = useMemo(() => layout.nodes.filter(isCard), [layout]);

  // Keep the roving tab stop on a card that exists.
  const stop = tabStop && cards.some(n => n.id === tabStop) ? tabStop : (focus && cards.some(n => n.id === focus) ? focus : cards[0]?.id ?? null);

  // Pan (keeping the zoom) so a card's top sits at `frac` of the canvas height.
  const revealCard = useCallback((id: string, frac: number) => {
    const n = rf.getNode(id);
    if (!n || !size.w) return;
    const { x, zoom } = rf.getViewport();
    const left = n.position.x * zoom + x, right = left + (n.width || 0) * zoom;
    const nx = left >= pad && right <= size.w - pad ? x : size.w / 2 - (n.position.x + (n.width || 0) / 2) * zoom;
    rf.setViewport({ x: nx, y: pad + frac * (size.h - 2 * pad) - n.position.y * zoom, zoom }, { duration: motion(280) });
  }, [rf, size, pad]);

  // A pan or zoom by the user that interrupts an animated framing leaves d3-zoom at an
  // in-between zoom: snap to the intended zoom when that gesture ends.
  const fitTarget = useRef<{ zoom: number; until: number } | null>(null);
  const setView = useCallback((v: { x: number; y: number; zoom: number }, duration: number) => {
    fitTarget.current = duration ? { zoom: v.zoom, until: performance.now() + duration } : null;
    rf.setViewport(v, { duration });
  }, [rf]);
  const interrupted = useRef(false);
  const onMoveStart = useCallback((e: unknown) => {
    const t = fitTarget.current;
    interrupted.current = !!e && !!t && performance.now() < t.until;
  }, []);
  const onMoveEnd = useCallback((e: unknown) => {
    const t = fitTarget.current;
    if (!e || !interrupted.current || !t) return;
    interrupted.current = false; fitTarget.current = null;
    if (Math.abs(rf.getZoom() - t.zoom) > 0.002) rf.zoomTo(t.zoom, { duration: motion(120) });
  }, [rf]);

  // Frame the layout after every change or canvas resize. If everything fits at a readable
  // zoom, show it all; otherwise fit the width at a readable zoom (or the floor) and frame
  // the overview's top-left or the focus card, leaving the rest to the "more" cues and
  // the group index. "Fit" in the toolbar always shows everything.
  useEffect(() => {
    if (!size.w || !layout.nodes.length) return;
    const raf = requestAnimationFrame(() => {
      const r = reveal.current;
      reveal.current = null;
      if (r && layout.nodes.some(n => n.id === r.id)) { revealCard(r.id, r.frac); return; }
      const W = viewW, H = viewH;
      const b = bounds(layout);
      const fitZ = Math.min(W / b.w, H / b.h);
      const duration = motion(FIT_MS);
      if (fitZ >= MIN_READABLE) {
        const zoom = Math.min(1, fitZ);
        setView({ x: pad + (W - b.w * zoom) / 2 - b.minX * zoom, y: pad + (H - b.h * zoom) / 2 - b.minY * zoom, zoom }, duration);
        return;
      }
      const zoom = Math.max(MIN_READABLE, Math.min(1, W / b.w));
      const f = focus ? layout.nodes.find(n => n.id === focus) : null;
      let left: number;
      if (b.w * zoom <= W) left = b.minX - (W / zoom - b.w) / 2;
      else if (f) left = f.position.x + (f.width || 0) / 2 - W / zoom / 2;
      else left = b.maxX - W / zoom;  // overview: keep the family column (and its "+N") whole; objectives clip left
      // focus: the card a third of the way down, so the nearest group above shows too,
      // without leaving empty canvas below the last group
      const top = f ? Math.max(b.minY, Math.min(f.position.y - FOCUS_TAG - (H / zoom) * 0.3, b.maxY - H / zoom)) : b.minY;
      setView({ x: pad - left * zoom, y: pad - top * zoom, zoom }, duration);
    });
    return () => cancelAnimationFrame(raf);
  }, [layout, focus, rf, size, pad, revealCard, setView]);  // eslint-disable-line react-hooks/exhaustive-deps

  const cardEl = (rfId: string) =>
    wrapRef.current?.querySelector<HTMLElement>(`[data-card="${CSS.escape(rfId)}"]`) || null;

  // After a re-focus, the card that had keyboard focus may be gone: move focus to the
  // new focus card (or the first card) so keyboard and screen-reader users stay in the graph.
  useEffect(() => {
    const p = pendingFocus.current;
    if (p === null) return;
    pendingFocus.current = null;
    const active = document.activeElement;
    if (active && active !== document.body && !wrapRef.current?.contains(active)) return;
    const raf = requestAnimationFrame(() => {
      const target = (p ? cardEl(p) : null) || (stop ? cardEl(stop) : null);
      target?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(raf);
  }, [layout]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Esc leaves full screen wherever focus is.
  useEffect(() => {
    if (!full || !onToggleFull) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onToggleFull(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [full, onToggleFull]);

  const ctx: GraphCtx = useMemo(() => ({
    atlas,
    select: id => select(id),
    // Open re-focuses the graph first, so it never stays on a card the reader is not showing.
    open: id => { select(id); onOpenRef.current(id); },
    toggleFamily: id => {
      reveal.current = { id, frac: 0.08 };
      setFamilies(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
    },
    toggleGroup: key => {
      // expanding: bring the first newly shown card (just after the summary card) to the top;
      // collapsing: keep the summary card in view
      const first = (layout.nodes.find(n => n.id === `more:${key}`)?.data as SummaryData | undefined)?.firstHidden;
      const expanding = !groups.has(key);
      reveal.current = expanding && first ? { id: first, frac: 0.05 } : { id: `more:${key}`, frac: 0.6 };
      pendingFocus.current = expanding && first ? first : `more:${key}`;
      setTabStop(pendingFocus.current);
      setGroups(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });
    },
    onCardFocus: (rfId, keyboard) => {
      setTabStop(rfId);
      // Tab focus can scroll React Flow's overflow-hidden container; undo it.
      const flow = wrapRef.current?.querySelector<HTMLElement>('.react-flow');
      if (flow) { flow.scrollTop = 0; flow.scrollLeft = 0; }
      if (!keyboard) return;  // pointer focus: the click's own re-layout handles the view
      const n = rf.getNode(rfId);
      const box = canvasRef.current?.getBoundingClientRect();
      if (!n || !box) return;
      const w = n.width || 0, h = n.height || 0;
      const tl = rf.flowToScreenPosition(n.position);
      const br = rf.flowToScreenPosition({ x: n.position.x + w, y: n.position.y + h });
      const inside = tl.x >= box.left + 4 && tl.y >= box.top + 4 && br.x <= box.right - 4 && br.y <= box.bottom - 4;
      if (!inside || rf.getZoom() < MIN_READABLE) {
        rf.setCenter(n.position.x + w / 2, n.position.y + h / 2, { zoom: Math.max(rf.getZoom(), MIN_READABLE), duration: motion(200) });
      }
    },
    moveFocus: (rfId, key) => {
      const from = layout.nodes.find(n => n.id === rfId);
      if (!from) return;
      const c = (n: GraphNode) => ({ x: n.position.x + (n.width || 0) / 2, y: n.position.y + (n.height || 0) / 2 });
      const a = c(from);
      const [dx, dy] = ({ ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] } as Record<string, number[]>)[key];
      let best: GraphNode | null = null, bestScore = Infinity;
      for (const n of layout.nodes) {
        if (n.id === rfId || !isCard(n)) continue;
        const b = c(n);
        const along = (b.x - a.x) * dx + (b.y - a.y) * dy;
        if (along <= 1) continue;
        const across = Math.abs((b.x - a.x) * dy) + Math.abs((b.y - a.y) * dx);
        const score = along + across * 2;
        if (score < bestScore) { best = n; bestScore = score; }
      }
      if (best) cardEl(best.id)?.focus();
    },
    setHot,
  }), [atlas, select, rf, layout, groups]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Hovered/focused card: show its edge labels and fade the rest (overview mainly;
  // a card inside a relation group has no edges of its own, so nothing changes).
  const edges = useMemo(() => {
    if (!hot || !layout.edges.some(e => e.source === hot || e.target === hot)) return layout.edges;
    return layout.edges.map(e => {
      const on = e.source === hot ? 'source' as const : e.target === hot ? 'target' as const : undefined;
      return { ...e, data: { ...e.data!, hot: on, dim: !on } };
    });
  }, [layout, hot]);

  const legendTypes = useMemo(() => {
    const present = new Set(layout.nodes.filter(n => n.type === 'card').map(n => atlas.nodes[(n.data as any).nodeId]?.type));
    return Object.entries(atlas.typeMeta).filter(([t]) => present.has(t)).sort((a, b) => a[1].order - b[1].order);
  }, [layout, atlas]);
  const legendEdges = useMemo(() => {
    const present = new Set(layout.edges.map(e => e.data?.cls));
    return EDGE_CLASSES.filter(c => present.has(c.id));
  }, [layout]);
  const hasCond = layout.edges.some(e => e.data?.cond) || layout.nodes.some(n => (n.data as any).conditional);
  const groupIndex = useMemo(
    () => layout.nodes.filter(n => n.type === 'relgroup').map(n => ({ id: n.id, ...(n.data as GroupData) })),
    [layout],
  );
  const lonely = !!focus && cards.length === 1;
  const offscreen = useOffscreen(cards, size);

  const toggleLegend = () => setLegendOpen(v => { writeLegendPref(!v); return !v; });
  const zoomBy = (f: number) => {
    const { zoom } = rf.getViewport();
    rf.zoomTo(Math.min(1.75, Math.max(0.08, zoom * f)), { duration: motion(200) });
  };
  // Fit shows everything (cards, lanes, the focus tag), however small.
  const fitAll = () => {
    const b = bounds(layout);
    const zoom = Math.max(0.08, Math.min(1, viewW / b.w, viewH / b.h));
    setView({ x: pad + (viewW - b.w * zoom) / 2 - b.minX * zoom, y: pad + (viewH - b.h * zoom) / 2 - b.minY * zoom, zoom }, motion(200));
  };
  const panBy = (dx: number, dy: number) => {
    const v = rf.getViewport();
    rf.setViewport({ ...v, x: v.x - dx, y: v.y - dy }, { duration: motion(240) });
  };

  // Trail: Overview > … > the last crumbs (fewer on phones), one row.
  const keep = trailAll ? TRAIL_MAX : compact ? 1 : 2;
  const shownTrail = trail.length > keep ? trail.slice(-keep) : trail;
  useEffect(() => { setTrailAll(false); }, [focus]);
  const goCrumb = (id: string) => {
    setTrail(t => t.slice(0, t.indexOf(id) + 1));
    setFocus(id); setGroups(new Set()); setTabStop(id);
    pendingFocus.current = id;
  };

  return (
    <GraphContext.Provider value={ctx}>
      <TabStopContext.Provider value={stop}>
        <div className="graphwrap" ref={wrapRef} data-mode={focus ? 'focus' : 'overview'}>
          <svg className="gdefs" aria-hidden="true" focusable="false">
            <defs>
              {EDGE_CLASSES.map(c => (
                <marker key={c.id} id={`garrow-${c.id}`} viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
                  <path d="M0,0.5 L10,5 L0,9.5 z" style={{ fill: `var(--gedge-${c.id})` }} />
                </marker>
              ))}
            </defs>
          </svg>

          <div className="gbar">
            <nav className="gtrail" aria-label="Graph trail">
              <button onClick={() => select(null)} aria-current={!focus ? 'true' : undefined}>
                <Network aria-hidden="true" /> Overview
              </button>
              {trail.length > keep && (
                <><ChevronRight className="gtrail__sep" aria-hidden="true" />
                  <button className="gtrail__more" onClick={() => setTrailAll(true)}
                    aria-label={`Show ${trail.length - keep} earlier step${trail.length - keep === 1 ? '' : 's'}: ${trail.slice(0, -keep).map(id => atlas.nodes[id]?.title).join(', ')}`}
                    title={trail.slice(0, -keep).map(id => atlas.nodes[id]?.title).join(' › ')}>…</button></>
              )}
              {shownTrail.map(id => (
                <React.Fragment key={id}>
                  <ChevronRight className="gtrail__sep" aria-hidden="true" />
                  {id === focus
                    ? <span className="gtrail__cur" aria-current="true" title={atlas.nodes[id]?.title}><span className="gtrail__txt">{atlas.nodes[id]?.title}</span></span>
                    : <button onClick={() => goCrumb(id)} title={atlas.nodes[id]?.title}><span className="gtrail__txt">{atlas.nodes[id]?.title}</span></button>}
                </React.Fragment>
              ))}
            </nav>
            {groupIndex.length > 1 && <GroupIndex groups={groupIndex} onJump={id => revealCard(id, 0.02)} />}
          </div>

          <div className="gcanvas" ref={canvasRef}>
            <ReactFlow
              nodes={layout.nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              colorMode={theme}
              nodesDraggable={false}
              nodesConnectable={false}
              nodesFocusable={false}
              edgesFocusable={false}
              elementsSelectable={false}
              disableKeyboardA11y
              deleteKeyCode={null}
              selectionKeyCode={null}
              multiSelectionKeyCode={null}
              zoomOnDoubleClick={false}
              panOnScroll
              minZoom={0.08}
              maxZoom={1.75}
              proOptions={PRO}
              ariaLabelConfig={ARIA_CONFIG}
              aria-label={focus ? `Graph focused on ${atlas.nodes[focus]?.title}` : 'Graph overview: objectives and technique families'}
              onMoveStart={onMoveStart}
              onMoveEnd={onMoveEnd}
            >
              {full && !compact && (
                <MiniMap pannable zoomable ariaLabel="Graph minimap"
                  nodeColor={n => (n.type === 'card' ? atlas.typeMeta[atlas.nodes[(n.data as any).nodeId]?.type]?.color || '#888' : 'transparent')}
                  nodeStrokeWidth={0} />
              )}
            </ReactFlow>
            <OffscreenFades out={offscreen} />
            <PinnedHead groups={layout.nodes} size={size} />
            {lonely && (
              <p className="gnote" role="status">
                No authored relationships yet. <button onClick={() => select(null)}>Back to the overview</button>
              </p>
            )}
            {legendOpen && (
              <div className="graph-legend" role="region" aria-label="Graph legend">
                <div className="graph-legend__top">
                  <b>Legend</b>
                  <button onClick={toggleLegend} aria-label="Close legend" title="Close legend"><X aria-hidden="true" /></button>
                </div>
                <div className="graph-legend__rows">
                  {legendTypes.map(([t, m]) => {
                    const G = glyphFor(m.glyph);
                    return <span key={t} className="graph-legend__type" style={{ ['--accent' as any]: m.color }}><G aria-hidden="true" />{m.label}</span>;
                  })}
                </div>
                <div className="graph-legend__rows">
                  {legendEdges.map(c => <span key={c.id}><EdgeSample cls={c.id} arrow={!!focus} />{c.label}</span>)}
                  {hasCond && <span><EdgeSample cls="cond" cond arrow={false} />Conditional (see the card)</span>}
                  {!focus && <span>Thicker line: more attacks; single-attack links show on hover</span>}
                </div>
                <div className="graph-legend__rows">
                  {Object.values(EVIDENCE).map(e => <span key={e.shape}><EvMark shape={e.shape} />{e.label}</span>)}
                </div>
                <div className="graph-legend__rows">
                  {COUNT_ICONS.map(({ Icon, label }) => <span key={label}><Icon aria-hidden="true" className="graph-legend__ico" />{label}</span>)}
                  <span><i className="gbadge gbadge--lab">LAB-01</i>Own hands-on lab</span>
                  <span><i className="gbadge">practiced</i>Practiced in a lab</span>
                  <span><i className="gbadge gbadge--also">×2</i>Also in an earlier group</span>
                </div>
              </div>
            )}
          </div>

          <div className="graph-tools" role="group" aria-label="Graph view controls">
            <button onClick={toggleLegend} aria-pressed={legendOpen} aria-label="Legend" title="Legend"><Info /><span>Legend</span></button>
            {focus && onList && (
              <button onClick={() => onList(focus)} aria-label="View relationships as list" title="View relationships as list">
                <ListIcon /><span>List</span>
              </button>
            )}
            <span className="graph-tools__gap" />
            <OffscreenPills out={offscreen} size={size} onPan={panBy} />
            <button onClick={() => zoomBy(1 / 1.25)} aria-label="Zoom out" title="Zoom out"><ZoomOut /></button>
            <button onClick={() => zoomBy(1.25)} aria-label="Zoom in" title="Zoom in"><ZoomIn /></button>
            <button onClick={fitAll} aria-label="Fit graph to view" title="Fit graph to view"><LocateFixed /><span>Fit</span></button>
            {onToggleFull && (
              <button onClick={onToggleFull} aria-pressed={!!full} aria-label={full ? 'Exit full screen graph' : 'Full screen graph'}
                title={full ? 'Exit full screen (Esc)' : 'Full screen'}>
                {full ? <Minimize2 /> : <Maximize2 />}
              </button>
            )}
          </div>
        </div>
      </TabStopContext.Provider>
    </GraphContext.Provider>
  );
}

// Cards lying outside the canvas, per direction.
type Out = { up: number; down: number; left: number; right: number };
function useOffscreen(cards: GraphNode[], size: { w: number; h: number }): Out {
  const [tx, ty, z] = useStore(s => s.transform);
  const out = { up: 0, down: 0, left: 0, right: 0 };
  if (!size.w) return out;
  for (const n of cards) {
    const l = n.position.x * z + tx, t = n.position.y * z + ty;
    const r = l + (n.width || 0) * z, b = t + (n.height || 0) * z;
    if (t >= size.h - 2) out.down++;
    else if (b <= 2) out.up++;
    else if (l >= size.w - 2) out.right++;
    else if (r <= 2) out.left++;
  }
  return out;
}

// Edge fades on the canvas where cards are clipped.
function OffscreenFades({ out }: { out: Out }) {
  return <>{(['up', 'down', 'left', 'right'] as const).map(d => out[d] > 0 && <div key={d} className={`gfade gfade--${d}`} aria-hidden="true" />)}</>;
}

// "N more" buttons in the toolbar strip (not over the cards); each pans that way.
function OffscreenPills({ out, size, onPan }: { out: Out; size: { w: number; h: number }; onPan: (dx: number, dy: number) => void }) {
  const where = { up: 'above', down: 'below', left: 'to the left', right: 'to the right' };
  const pill = (dir: keyof Out, Icon: React.ComponentType<any>, dx: number, dy: number) => out[dir] > 0 && (
    <button key={dir} className="gmore" onClick={() => onPan(dx, dy)}
      aria-label={`Show ${out[dir]} more card${out[dir] === 1 ? '' : 's'} ${where[dir]}`} title={`${out[dir]} more ${where[dir]}`}>
      <Icon aria-hidden="true" />{out[dir]}
    </button>
  );
  return (
    <>
      {pill('up', ArrowUp, 0, -size.h * 0.7)}
      {pill('down', ArrowDown, 0, size.h * 0.7)}
      {pill('left', ArrowLeft, -size.w * 0.7, 0)}
      {pill('right', ArrowRight, size.w * 0.7, 0)}
    </>
  );
}

// While a group's header is scrolled above the canvas and its cards still fill it,
// pin a copy of the header to the top so the cards keep their relation label.
function PinnedHead({ groups, size }: { groups: GraphNode[]; size: { w: number; h: number } }) {
  const [, ty, z] = useStore(s => s.transform);
  if (!size.w) return null;
  let pinned: GraphNode | null = null;
  for (const n of groups) {
    if (n.type !== 'relgroup') continue;
    const top = n.position.y * z + ty, bottom = (n.position.y + (n.height || 0)) * z + ty;
    if (top < -4 && bottom > 60) pinned = n;
  }
  if (!pinned) return null;
  return <div className="gpinned" aria-hidden="true"><GroupHead data={pinned.data as GroupData} pinned /></div>;
}

// Relation-group chips: one tab stop, arrow keys move along the row (roving tabindex).
function GroupIndex({ groups, onJump }: { groups: ({ id: string } & GroupData)[]; onJump: (id: string) => void }) {
  const [cur, setCur] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const at = Math.min(cur, groups.length - 1);
  const onKeyDown = (e: React.KeyboardEvent) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1, Home: -Infinity, End: Infinity }[e.key];
    if (step === undefined) return;
    e.preventDefault();
    const i = Math.max(0, Math.min(groups.length - 1, Number.isFinite(step) ? at + step : step < 0 ? 0 : groups.length - 1));
    setCur(i);
    refs.current[i]?.focus();
  };
  return (
    <div className="gindex" role="toolbar" aria-label="Jump to relation group" onKeyDown={onKeyDown}>
      {groups.map((g, i) => (
        <button key={g.id} ref={el => { refs.current[i] = el; }} tabIndex={i === at ? 0 : -1}
          onFocus={() => setCur(i)} onClick={() => onJump(g.id)} title={`Show ${g.label}`}>
          <EdgeSample cls={g.cls} arrow={false} />{g.label} <b>{g.count}</b>
        </button>
      ))}
    </div>
  );
}

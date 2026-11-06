// Custom React Flow node and edge renderers for the atlas graph.

import React, { createContext, useContext } from 'react';
import { Handle, Position, BaseEdge, EdgeLabelRenderer, type NodeProps, type EdgeProps } from '@xyflow/react';
import {
  ArrowUpRight, Plus, Minus, ShieldCheck, Gauge, Crosshair, Layers, Target, SquareTerminal, Link2, ChevronsDown, ChevronsUp, GitFork,
} from 'lucide-react';
import { type Atlas, type AtlasNode, glyphFor } from '../atlas';
import type { GraphNode, CardData, SummaryData, GroupData, ColHeadData, GraphEdge, EdgeClass } from './layout';

export interface GraphCtx {
  atlas: Atlas;
  select: (id: string) => void;         // re-focus inside the graph
  open: (id: string) => void;           // load in the reader (+ /nodes/<id>/)
  toggleFamily: (id: string) => void;   // overview: expand/collapse member attacks
  toggleGroup: (key: string) => void;   // focus: show all / fewer cards in a relation group
  onCardFocus: (rfId: string, keyboard: boolean) => void;  // roving tab stop; keep a keyboard-focused card in view
  moveFocus: (rfId: string, key: string) => void;  // arrow-key navigation between cards
  setHot: (rfId: string | null) => void;            // hovered/focused card: emphasize its edges
}
export const GraphContext = createContext<GraphCtx | null>(null);
const useGraph = () => useContext(GraphContext)!;
// Roving tab index: the one card that takes Tab (the graph is a single tab stop; arrows move inside).
export const TabStopContext = createContext<string | null>(null);

// Evidence marker: shape carries the meaning, not color (full / half / empty circle).
export const EVIDENCE: Record<string, { shape: 'full' | 'half' | 'empty'; label: string }> = {
  source_linked: { shape: 'full', label: 'Source-linked evidence' },
  metadata_and_abstract: { shape: 'half', label: 'Partial evidence (metadata and abstract)' },
  synthesis_requires_case_evidence: { shape: 'empty', label: 'Synthesis, needs case evidence' },
};
// Drawn as SVG so the shapes do not depend on the font.
export function EvMark({ shape }: { shape: 'full' | 'half' | 'empty' }) {
  return (
    <svg className="gev" viewBox="0 0 10 10" aria-hidden="true" focusable="false">
      <circle cx="5" cy="5" r="4.1" className={shape === 'full' ? 'gev__fill' : 'gev__ring'} />
      {shape === 'half' && <path d="M5,0.9 A4.1,4.1 0 0 0 5,9.1 z" className="gev__half" />}
    </svg>
  );
}

// Footer count icons, explained in the legend.
export const COUNT_ICONS: { Icon: React.ComponentType<any>; label: string }[] = [
  { Icon: Crosshair, label: 'Attacks' }, { Icon: ShieldCheck, label: 'Defenses' }, { Icon: Gauge, label: 'Evaluations' },
  { Icon: Layers, label: 'Families' }, { Icon: Target, label: 'Objectives' }, { Icon: SquareTerminal, label: 'Labs' },
  { Icon: GitFork, label: 'Dependents' }, { Icon: Link2, label: 'Sources' },
];

const LEVEL: Record<string, string> = { beginner: 'beg', intermediate: 'int', advanced: 'adv' };
const shortTime = (t: string) => t.replace(/\s*min(utes)?$/, 'm').replace(/\s*h(ours?)?$/, 'h');

// Footer counts per node type: [rel key, icon, singular, plural].
type CountSpec = [string, React.ComponentType<any>, string, string];
const COUNTS: Record<string, CountSpec[]> = {
  goal: [['reachableVia', Crosshair, 'attack', 'attacks']],
  technique_family: [['hasMember', Crosshair, 'attack', 'attacks']],
  attack: [['mitigatedBy', ShieldCheck, 'defense', 'defenses'], ['evaluatedBy', Gauge, 'evaluation', 'evaluations']],
  defense: [['canMitigate', Crosshair, 'attack mitigated', 'attacks mitigated']],
  evaluation: [['evaluates', Crosshair, 'attack evaluated', 'attacks evaluated']],
  method: [['usedBy', Crosshair, 'user', 'users']],
};
const GENERIC: CountSpec[] = [['hasRelevantTopic', Crosshair, 'relevant topic', 'relevant topics'], ['requiredBy', GitFork, 'dependent', 'dependents']];

function countsOf(atlas: Atlas, n: AtlasNode) {
  const out = (COUNTS[n.type] || GENERIC)
    .map(([k, Icon, one, many]) => ({ k, Icon, n: n.rel?.[k]?.length || 0, one, many }))
    .filter(c => c.n > 0 || COUNTS[n.type]);
  if (n.type === 'goal') {
    const fams = atlas.familyGoals.filter(fg => fg.goal === n.id).length;
    out.push({ k: 'families', Icon: Layers, n: fams, one: 'family', many: 'families' });
  }
  if (n.type === 'technique_family') {
    const goals = atlas.familyGoals.filter(fg => fg.family === n.id).length;
    out.push({ k: 'goals', Icon: Target, n: goals, one: 'objective', many: 'objectives' });
  }
  if (n.type === 'goal' || n.type === 'technique_family') {
    out.push({ k: 'labs', Icon: SquareTerminal, n: n.labs_in_area?.length || 0, one: 'lab', many: 'labs' });
  }
  return out;
}

function Handles() {
  return (
    <>
      <Handle type="target" position={Position.Top} isConnectable={false} className="gcard__handle" />
      <Handle type="source" position={Position.Bottom} isConnectable={false} className="gcard__handle" />
    </>
  );
}

const ARROWS = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
const isKeyboardFocus = (el: Element) => { try { return el.matches(':focus-visible'); } catch { return true; } };

export const CardNode = React.memo(function CardNode({ id, data }: NodeProps<GraphNode & { data: CardData }>) {
  const { atlas, select, open, toggleFamily, onCardFocus, moveFocus, setHot } = useGraph();
  const tabStop = useContext(TabStopContext);
  const n = atlas.nodes[data.nodeId];
  if (!n) return null;
  const meta = atlas.typeMeta[n.type];
  const Glyph = glyphFor(meta?.glyph || 'BookOpen');
  const ev = EVIDENCE[n.evidence_status];
  const refs = n.references?.length || 0;
  const counts = countsOf(atlas, n);
  const lab = n.lab ? `${n.lab.lab_id} · ${LEVEL[n.lab.level] || n.lab.level} · ${shortTime(n.lab.time)}` : '';
  const countText = counts.map(c => `${c.n} ${c.n === 1 ? c.one : c.many}`).join(', ');
  const aria = [
    data.group || '',
    `${meta?.label || n.type}: ${n.title}`,
    data.focus ? 'current focus' : '',
    data.also ? `also listed under ${data.also}` : '',
    data.via || '',
    countText,
    lab ? `hands-on lab ${lab}` : n.practiced_in ? `practiced in ${n.practiced_in.lab_id}` : '',
    ev ? ev.label : '',
    refs ? `${refs} source${refs === 1 ? '' : 's'}` : '',
    data.conditional ? `conditional: ${data.conditional}` : '',
    data.expand ? `${data.expand.count} member attacks ${data.expand.expanded ? 'shown' : 'hidden'}, press plus or minus to toggle` : '',
    data.focus ? 'Enter opens in the reader' : 'Space focuses the graph here, Enter opens in the reader',
  ].filter(Boolean).join('. ');

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.target !== e.currentTarget) return;  // keys on the inner buttons keep their native behaviour
    if (e.key === 'Enter') { e.preventDefault(); open(n.id); }
    else if (e.key === ' ') { e.preventDefault(); if (!data.focus) select(n.id); }
    else if (data.expand && (e.key === '+' || e.key === '-' || e.key === '=')) {
      e.preventDefault();
      if ((e.key === '-') === data.expand.expanded) toggleFamily(n.id);
    } else if (ARROWS.includes(e.key)) { e.preventDefault(); moveFocus(id, e.key); }
  };

  return (
    <div className="gcard nodrag" data-card={id} data-focus={data.focus ? 'true' : undefined}
      style={{ ['--accent' as any]: meta?.color }} tabIndex={tabStop === id ? 0 : -1} role="group" aria-roledescription="graph card"
      aria-label={aria} title={n.title}
      onClick={() => { if (!data.focus) select(n.id); }}
      onKeyDown={onKeyDown}
      onFocus={e => { if (e.target === e.currentTarget) onCardFocus(id, isKeyboardFocus(e.currentTarget)); setHot(id); }}
      onBlur={() => setHot(null)}
      onMouseEnter={() => setHot(id)} onMouseLeave={() => setHot(null)}>
      <Handles />
      <div className="gcard__head">
        <span className="gcard__type"><Glyph aria-hidden="true" />{meta?.label || n.type}</span>
        {data.also && <span className="gbadge gbadge--also" title={`Also listed under ${data.also}`} aria-hidden="true">×2</span>}
        <span className="gcard__meta" aria-hidden="true">
          {ev && <span className="gcard__ev" title={ev.label}><EvMark shape={ev.shape} /></span>}
          {refs > 0 && <span className="gcard__refs" title={`${refs} source${refs === 1 ? '' : 's'}`}><Link2 />{refs}</span>}
        </span>
        <button className="gcard__open" tabIndex={-1} aria-label={`Open ${n.title} in the reader`} title="Open in reader"
          onClick={e => { e.stopPropagation(); open(n.id); }}>
          <ArrowUpRight aria-hidden="true" />
        </button>
      </div>
      <div className="gcard__title">{n.title}</div>
      <div className="gcard__foot">
        {lab
          ? <span className="gbadge gbadge--lab" title={`Hands-on lab: ${n.lab!.title}`} aria-hidden="true">{lab}</span>
          : n.practiced_in && <span className="gbadge" title={`Practiced in ${n.practiced_in.lab_id}, steps ${n.practiced_in.steps}`} aria-hidden="true">practiced</span>}
        {data.conditional && <span className="gbadge gbadge--cond" title={`Conditional: ${data.conditional}`} aria-hidden="true">conditional</span>}
        {data.via && <span className="gbadge gbadge--via" title={data.via} aria-hidden="true">{data.via}</span>}
        {counts.map(c => (c.k === 'mitigatedBy' && c.n === 0
          // an attack with no defense is the gap worth seeing: a labelled warning chip, not a muted zero
          ? <span key={c.k} className="gcard__count gcard__count--none" title="No defenses mapped yet" aria-hidden="true"><c.Icon />0</span>
          : <span key={c.k} className="gcard__count" title={`${c.n} ${c.n === 1 ? c.one : c.many}`} aria-hidden="true"><c.Icon />{c.n}</span>
        ))}
        {data.expand && (
          <button className="gcard__expand" tabIndex={-1} aria-label={`${data.expand.expanded ? 'Hide' : 'Show'} ${data.expand.count} attacks of ${n.title}`}
            title={data.expand.expanded ? 'Hide member attacks' : 'Show member attacks'} aria-expanded={data.expand.expanded}
            onClick={e => { e.stopPropagation(); toggleFamily(n.id); }}>
            {data.expand.expanded ? <Minus /> : <Plus />}{data.expand.count}
          </button>
        )}
      </div>
    </div>
  );
});

export const SummaryNode = React.memo(function SummaryNode({ id, data }: NodeProps<GraphNode & { data: SummaryData }>) {
  const { toggleGroup, onCardFocus, moveFocus } = useGraph();
  const tabStop = useContext(TabStopContext);
  const label = data.expanded ? `Show fewer · ${data.label}` : `+${data.hidden} more · ${data.label}`;
  return (
    <button className="gcard gcard--more nodrag" data-card={id} onClick={() => toggleGroup(data.groupKey)} tabIndex={tabStop === id ? 0 : -1}
      aria-expanded={data.expanded} aria-label={data.expanded ? `Show fewer ${data.label}` : `Show ${data.hidden} more ${data.label}`}
      onFocus={e => onCardFocus(id, isKeyboardFocus(e.currentTarget))}
      onKeyDown={e => { if (ARROWS.includes(e.key)) { e.preventDefault(); moveFocus(id, e.key); } }}>
      {data.expanded ? <ChevronsUp aria-hidden="true" /> : <ChevronsDown aria-hidden="true" />}
      <span>{label}</span>
    </button>
  );
});

// Dash sample matching a connector class (group headers, legend).
export function EdgeSample({ cls, cond, arrow = true }: { cls: EdgeClass | 'cond'; cond?: boolean; arrow?: boolean }) {
  return (
    <svg className="gline" viewBox="0 0 30 10" aria-hidden="true" focusable="false">
      <line x1="1" y1="5" x2={arrow ? 21 : 29} y2="5" className={`gedge gedge--${cls}`} />
      {arrow && <path d="M20,1.5 L29,5 L20,8.5 z" style={{ fill: `var(--gedge-${cls})` }} />}
      {cond && <path d="M11,5 L15,1.5 L19,5 L15,8.5 z" className="gedge__cond" />}
    </svg>
  );
}

export function GroupNode({ data }: NodeProps<GraphNode & { data: GroupData }>) {
  return (
    <div className="ggroup" data-cls={data.cls}>
      <Handles />
      <GroupHead data={data} />
    </div>
  );
}

// Group header: also drawn pinned to the top of the canvas while the group's cards fill it.
// An expanded group gets a "Show fewer" control here, so collapsing never needs a long scroll
// (pointer only; keyboard users have the summary card, which keeps its place).
export function GroupHead({ data, pinned }: { data: GroupData; pinned?: boolean }) {
  const { toggleGroup } = useGraph();
  return (
    <div className={`ggroup__head${pinned ? ' ggroup__head--pinned' : ''}`}>
      <EdgeSample cls={data.cls} arrow={false} />
      <span>{data.label}</span><span className="ggroup__n">({data.count})</span>
      {data.conditional > 0 && (
        <span className="ggroup__cond" title={`${data.conditional} of ${data.count} hold only under stated conditions (see the cards)`}>
          <span aria-hidden="true">◇</span> {data.conditional} cond.
        </span>
      )}
      {data.expanded && (
        <button className="ggroup__less nodrag" tabIndex={-1} onClick={() => toggleGroup(data.key)} title={`Show fewer ${data.label}`}>
          <ChevronsUp aria-hidden="true" />Show fewer
        </button>
      )}
    </div>
  );
}

export function ColHeadNode({ data }: NodeProps<GraphNode & { data: ColHeadData }>) {
  return <div className="gcolhead" aria-hidden="true">{data.label}</div>;
}

type Pt = { x: number; y: number };

// Orthogonal polyline with rounded corners.
function elbowPath(pts: Pt[], r = 10): string {
  let d = `M${pts[0].x},${pts[0].y}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const [p, c, n] = [pts[i - 1], pts[i], pts[i + 1]];
    const k = Math.min(r, Math.hypot(c.x - p.x, c.y - p.y) / 2, Math.hypot(n.x - c.x, n.y - c.y) / 2);
    const a = { x: c.x - Math.sign(c.x - p.x) * k, y: c.y - Math.sign(c.y - p.y) * k };
    const b = { x: c.x + Math.sign(n.x - c.x) * k, y: c.y + Math.sign(n.y - c.y) * k };
    d += `L${a.x},${a.y}Q${c.x},${c.y} ${b.x},${b.y}`;
  }
  const last = pts[pts.length - 1];
  return d + `L${last.x},${last.y}`;
}

function hCurve([a, b]: Pt[]): string {
  const mx = (a.x + b.x) / 2;
  return `M${a.x},${a.y}C${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`;
}

export function AtlasEdge({ id, data }: EdgeProps<GraphEdge>) {
  if (!data) return null;
  const path = data.curve === 'h' ? hCurve(data.points) : elbowPath(data.points);
  const marker = `url(#garrow-${data.cls})`;
  // Conditional connector: keeps its class colour and dash, plus a hollow diamond on its lane.
  const mid = data.cond && data.points.length >= 3
    ? { x: (data.points[1].x + data.points[2].x) / 2, y: (data.points[1].y + data.points[2].y) / 2 } : null;
  // Label beside the far end's port: hovering an objective labels each family end, and vice versa.
  const at = data.hot === 'source' ? data.labelAtTarget : data.hot === 'target' ? data.labelAtSource : undefined;
  return (
    <>
      <BaseEdge id={id} path={path}
        className={`gedge gedge--${data.cls}${data.weak ? ' is-weak' : ''}${data.hot ? ' is-hot' : ''}${data.dim ? ' is-dim' : ''}`}
        interactionWidth={14}
        markerEnd={data.arrow === 'end' ? marker : undefined}
        markerStart={data.arrow === 'start' ? marker : undefined}
        style={{ strokeWidth: data.width }} />
      {mid && (
        <path className="gedge__cond" d={`M${mid.x - 6},${mid.y} L${mid.x},${mid.y - 6} L${mid.x + 6},${mid.y} L${mid.x},${mid.y + 6} z`}>
          <title>{data.title}</title>
        </path>
      )}
      {data.label && at && (
        <EdgeLabelRenderer>
          <div className="gedge__label nodrag nopan" title={data.title}
            style={{ transform: `translate(${data.hot === 'source' ? '-100%' : '0'}, -50%) translate(${at.x}px, ${at.y}px)` }}>
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
      {data.title && !data.label && !mid && <title>{data.title}</title>}
    </>
  );
}

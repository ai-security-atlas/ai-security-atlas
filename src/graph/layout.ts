// Deterministic layouts for the atlas graph (no physics). Pure functions:
// atlas + UI state in, positioned React Flow nodes/edges out. Edges carry their
// own points so the renderer draws exactly what was laid out.

import type { Node, Edge } from '@xyflow/react';
import type { Atlas } from '../atlas';

export const CARD_W = 212;
export const CARD_H = 104;
export const GROUP_CAP = 6;          // cards shown per relation group before "+N more"
const GAP = 12;                      // between cards inside a group
const PAD = 10;                      // group box padding
const HEAD = 30;                     // group box header (relation label)

// Five visual edge classes (legend order).
export type EdgeClass = 'hierarchy' | 'mitigates' | 'evaluates' | 'scope' | 'lateral';
export const EDGE_CLASSES: { id: EdgeClass; label: string }[] = [
  { id: 'hierarchy', label: 'Serves objective / member of' },
  { id: 'mitigates', label: 'Mitigates (to defenses)' },
  { id: 'evaluates', label: 'Evaluates (to evaluations)' },
  { id: 'scope', label: 'Scope / requires / uses' },
  { id: 'lateral', label: 'Variant / enables / distinct' },
];
const CLASS_OF: Record<string, EdgeClass> = {
  can_serve_goal: 'hierarchy', member_of: 'hierarchy',
  can_mitigate: 'mitigates', evaluated_by: 'evaluates',
  in_scope_of: 'scope', requires_concept: 'scope', uses: 'scope',
  variant_of: 'lateral', can_enable: 'lateral', distinct_from: 'lateral',
  family_goal: 'hierarchy',  // derived from familyGoals (overview edges, focus on an objective or family)
};

// Relation group (reader rel key) -> authored edge type, whether the focus is the
// edge source, the rank band relative to the focus (<0 above, >0 below) and the
// connector label.
export const REL_SPEC: Record<string, { type: string; out: boolean; band: number; label: string }> = {
  routesToGoal: { type: 'can_serve_goal', out: true, band: -2, label: 'Serves objective' },
  memberOf: { type: 'member_of', out: true, band: -1, label: 'Member of' },
  canMitigate: { type: 'can_mitigate', out: true, band: -1, label: 'Mitigates' },
  evaluates: { type: 'evaluated_by', out: false, band: -1, label: 'Evaluates' },
  usedBy: { type: 'uses', out: false, band: -1, label: 'Used by' },
  hasRelevantTopic: { type: 'in_scope_of', out: false, band: -1, label: 'Relevant topics' },
  requiredBy: { type: 'requires_concept', out: false, band: -1, label: 'Required by' },
  variantOf: { type: 'variant_of', out: true, band: -1, label: 'Variant of' },
  mayBeEnabledBy: { type: 'can_enable', out: false, band: -1, label: 'Enabled by' },
  reachableVia: { type: 'can_serve_goal', out: false, band: 1, label: 'Reached via' },
  hasMember: { type: 'member_of', out: false, band: 1, label: 'Techniques' },
  mitigatedBy: { type: 'can_mitigate', out: false, band: 1, label: 'Defended by' },
  evaluatedBy: { type: 'evaluated_by', out: true, band: 2, label: 'Evaluated by' },
  inScopeOf: { type: 'in_scope_of', out: true, band: 3, label: 'In scope of' },
  requires: { type: 'requires_concept', out: true, band: 3, label: 'Requires' },
  uses: { type: 'uses', out: true, band: 3, label: 'Uses' },
  hasVariant: { type: 'variant_of', out: false, band: 4, label: 'Variants' },
  canEnable: { type: 'can_enable', out: true, band: 4, label: 'Can enable' },
  distinctFrom: { type: 'distinct_from', out: true, band: 4, label: 'Distinct from' },
};
const REL_KEYS = Object.keys(REL_SPEC);

export interface CardData extends Record<string, unknown> {
  nodeId: string;
  via?: string;                               // derived family <-> objective link: "via N attacks"
  focus?: boolean;
  group?: string;                             // focus mode: "Defended by, 2 of 4" (accessible name)
  also?: string;                              // the same node also sits in this earlier group
  conditional?: string;                       // edge condition text toward the focus
  expand?: { count: number; expanded: boolean };  // overview family: member attacks
}
export interface SummaryData extends Record<string, unknown> {
  groupKey: string; hidden: number; label: string; expanded: boolean;
  firstHidden: string;                        // card id of the first card past the cap
}
export interface GroupData extends Record<string, unknown> {
  key: string; label: string; count: number; cls: EdgeClass; conditional: number;
  expanded?: boolean; hidden?: number;        // set when the group is over GROUP_CAP
}
export interface ColHeadData extends Record<string, unknown> { label: string }
export interface AtlasEdgeData extends Record<string, unknown> {
  points: { x: number; y: number }[];
  cls: EdgeClass;
  width: number;
  arrow: 'start' | 'end' | 'none';
  cond?: boolean;                             // every relation in this connector is conditional
  weak?: boolean;                             // overview edge backed by a single attack: hidden at rest, shown on hover/focus
  curve?: 'h' | 'elbow';                      // 'h': S-curve between two points; 'elbow': rounded orthogonal polyline
  hot?: 'source' | 'target';                  // which endpoint card is hovered/focused: label shown at the other end
  dim?: boolean;                              // another card is hovered/focused
  label?: string;
  labelAtSource?: { x: number; y: number };   // label anchor beside the source port (left-aligned)
  labelAtTarget?: { x: number; y: number };   // label anchor beside the target port (right-aligned)
  title?: string;                             // condition text / tooltip
}
export type GraphNode =
  | Node<CardData, 'card'> | Node<SummaryData, 'summary'> | Node<GroupData, 'relgroup'> | Node<ColHeadData, 'colhead'>;
export type GraphEdge = Edge<AtlasEdgeData, 'atlas'>;
export interface GraphLayout { nodes: GraphNode[]; edges: GraphEdge[] }

// React Flow wraps every node in a div with aria-roledescription="node" and no
// role, which is invalid ARIA; the card inside carries the semantics.
const QUIET = { ariaRole: 'presentation' as const, domAttributes: { 'aria-roledescription': undefined } as any };

// Condition text per authored edge, cached per atlas.
const condCache = new WeakMap<Atlas, Map<string, string>>();
function conditionOf(atlas: Atlas, type: string, s: string, t: string): string {
  let m = condCache.get(atlas);
  if (!m) {
    m = new Map();
    for (const e of atlas.edges) if (e.conditions) m.set(`${e.type}|${e.source}|${e.target}`, e.conditions);
    condCache.set(atlas, m);
  }
  return m.get(`${type}|${s}|${t}`) || '';
}

/* ------------------------------------------------------------- overview */

export const GUTTER = { narrow: 44, wide: 72 };  // between the objective and family columns (edges run here)
const ROW = 14;        // vertical gap between cards in a column
const INDENT = 14;     // expanded member attacks sit indented under their family
const PORT = 8;        // spacing between edge ports along a card side
const COLHEAD = 30;    // column caption height above the cards

// Objectives (left column, GOAL_ORDER, even pitch) -> technique families (right
// column) joined by the derived familyGoals edges; "+N" lists a family's member
// attacks indented under it, so all three ranks stay in view. Left to right
// because thirteen families in one row would not fit a side pane. Families are
// ordered by the weighted barycentre of the objectives they serve, which keeps
// most edges short; each card spreads its edge ports along its side so the
// edges stay distinguishable. No arrowheads: the column order gives the
// direction. "via N attacks" labels show on hover/focus of either end card,
// beside the far end's port; edge thickness carries the count at rest.
export function buildOverview(atlas: Atlas, expanded: Set<string>, gutter = GUTTER.wide): GraphLayout {
  const goals = atlas.nav.objectives.map(o => o.goalId).filter(id => atlas.nodes[id]);
  const fgEdges = atlas.familyGoals.filter(fg => atlas.nodes[fg.goal] && atlas.nodes[fg.family] && goals.includes(fg.goal));
  const famOrder: string[] = [];
  for (const fg of fgEdges) if (!famOrder.includes(fg.family)) famOrder.push(fg.family);
  const gi = new Map(goals.map((g, i) => [g, i]));
  const bary = new Map(famOrder.map(f => {
    const es = fgEdges.filter(e => e.family === f);
    const w = es.reduce((s, e) => s + e.attack_count, 0) || 1;
    return [f, es.reduce((s, e) => s + gi.get(e.goal)! * e.attack_count, 0) / w];
  }));
  const families = [...famOrder].sort((a, b) => bary.get(a)! - bary.get(b)! || famOrder.indexOf(a) - famOrder.indexOf(b));

  const pitch = CARD_H + ROW;
  const famX = CARD_W + gutter;
  // Both columns top-aligned under their captions.
  const pos = new Map<string, { x: number; y: number }>();
  goals.forEach((id, i) => pos.set(id, { x: 0, y: i * pitch }));
  let y = 0;
  const attacks: { id: string; family: string }[] = [];
  for (const fam of families) {
    pos.set(fam, { x: famX, y });
    y += pitch;
    if (!expanded.has(fam)) continue;
    for (const a of atlas.nodes[fam].rel?.hasMember || []) {
      if (!atlas.nodes[a] || pos.has(a)) continue;
      pos.set(a, { x: famX + INDENT, y });
      attacks.push({ id: a, family: fam });
      y += CARD_H + 10;
    }
    y += 6;
  }

  const card = (id: string, extra: Partial<CardData> = {}, w = CARD_W): GraphNode =>
    ({ id, type: 'card', position: pos.get(id)!, width: w, height: CARD_H, data: { nodeId: id, ...extra }, ...QUIET });
  const top = Math.min(...[...pos.values()].map(p => p.y));
  const nodes: GraphNode[] = [
    { id: 'col:goals', type: 'colhead', position: { x: 0, y: top - COLHEAD }, width: CARD_W, height: 22,
      data: { label: 'Adversary objectives' }, selectable: false, focusable: false, ...QUIET },
    { id: 'col:families', type: 'colhead', position: { x: famX, y: top - COLHEAD }, width: CARD_W, height: 22,
      data: { label: 'Technique families' }, selectable: false, focusable: false, ...QUIET },
    ...goals.map(id => card(id)),
    ...families.map(id => {
      const count = atlas.nodes[id].rel?.hasMember?.length || 0;
      return card(id, count ? { expand: { count, expanded: expanded.has(id) } } : {});
    }),
    ...attacks.map(a => card(a.id, {}, CARD_W - INDENT)),  // indented, same right edge as the family
  ];
  // Reading order (arrow keys, screen readers): objectives column, then families with their attacks.
  const col = (n: GraphNode) => (n.position.x >= famX ? 1 : 0);
  nodes.sort((a, b) => col(a) - col(b) || a.position.y - b.position.y);

  // Edge ports: each card's edges leave/enter at distinct heights, ordered by the
  // other end's position so neighbouring edges do not cross at the card.
  const ports = (id: string, others: string[]) => {
    const sorted = [...others].sort((a, b) => pos.get(a)!.y - pos.get(b)!.y);
    const step = Math.min(PORT, (CARD_H - 24) / Math.max(1, sorted.length - 1));
    const mid = pos.get(id)!.y + CARD_H / 2;
    return new Map(sorted.map((o, i) => [o, mid + (i - (sorted.length - 1) / 2) * step]));
  };
  const goalPorts = new Map(goals.map(g => [g, ports(g, fgEdges.filter(e => e.goal === g).map(e => e.family))]));
  const famPorts = new Map(families.map(f => [f, ports(f, fgEdges.filter(e => e.family === f).map(e => e.goal))]));

  // At rest only links backed by 2+ attacks are drawn (a single-attack link shows on
  // hover/focus of either card), unless it is the only link a card has.
  const degree = (k: 'goal' | 'family', v: string) => fgEdges.filter(e => e[k] === v).length;
  const edges: GraphEdge[] = [
    ...fgEdges.map(fg => {
      const a = { x: CARD_W, y: goalPorts.get(fg.goal)!.get(fg.family)! };
      const b = { x: famX, y: famPorts.get(fg.family)!.get(fg.goal)! };
      const label = `via ${fg.attack_count} attack${fg.attack_count === 1 ? '' : 's'}`;
      const title = `${atlas.nodes[fg.family].title} serves ${atlas.nodes[fg.goal].title} ${label}`;
      return {
        id: `fg:${fg.goal}:${fg.family}`, source: fg.goal, target: fg.family, type: 'atlas' as const, ariaLabel: title,
        data: {
          points: [a, b], curve: 'h' as const, cls: 'hierarchy' as EdgeClass,
          // thinner in the narrow gutter (phones), where the lines otherwise merge into one band
          width: gutter < GUTTER.wide ? 1 + Math.min(1.5, fg.attack_count * 0.2) : 1 + Math.min(3, fg.attack_count * 0.4),
          arrow: 'none' as const, label, title,
          weak: fg.attack_count === 1 && degree('goal', fg.goal) > 1 && degree('family', fg.family) > 1,
          labelAtSource: { x: a.x + 6, y: a.y }, labelAtTarget: { x: b.x - 6, y: b.y },
        },
      };
    }),
    ...attacks.map(a => {
      const f = pos.get(a.family)!, t = pos.get(a.id)!;
      const rail = f.x + INDENT / 2;
      return {
        id: `m:${a.family}:${a.id}`, source: a.family, target: a.id, type: 'atlas' as const,
        ariaLabel: `${atlas.nodes[a.id].title} is a member of ${atlas.nodes[a.family].title}`,
        data: {
          points: [{ x: rail, y: f.y + CARD_H }, { x: rail, y: t.y + CARD_H / 2 }, { x: t.x, y: t.y + CARD_H / 2 }],
          curve: 'elbow' as const, cls: 'hierarchy' as EdgeClass, width: 1.5, arrow: 'none' as const,
        },
      };
    }),
  ];
  return { nodes, edges };
}

/* ---------------------------------------------------------------- focus */

const VGAP = 30;      // between stacked group boxes
const COLGAP = 40;    // between the two group columns (wide canvases)
// Score a candidate layout by its fit zoom only if its width stays near full size.
const MIN_FIT = 0.9;

// Derived relation (not authored): the familyGoals roll-up the overview draws.
const FAMILY_GOAL = 'family_goal';
const DERIVED_SPEC = {
  goalFamilies: { type: FAMILY_GOAL, out: false, band: 0.5, label: 'Families' },        // goal focus: below, before "Reached via"
  familyGoals: { type: FAMILY_GOAL, out: true, band: -2, label: 'Serves objective' },   // family focus: above
};

interface Rel { key: string; spec: { type: string; out: boolean; band: number; label: string }; ids: string[]; via?: Map<string, string> }
interface Sized extends Rel { expanded: boolean; cells: (string | null)[]; cols: number; w: number; h: number }  // null = summary card
interface Placed { g: Sized; x: number; y: number; side: 1 | -1; k: number }

const viaText = (n: number) => `via ${n} attack${n === 1 ? '' : 's'}`;

function relationsOf(atlas: Atlas, id: string): Rel[] {
  const focus = atlas.nodes[id];
  const out: Rel[] = REL_KEYS
    .map(k => ({ key: k, spec: REL_SPEC[k], ids: (focus.rel?.[k] || []).filter(n => atlas.nodes[n]) }))
    .filter(r => r.ids.length);
  // Objectives and families also show the family <-> objective links the overview draws.
  if (focus.type === 'goal' || focus.type === 'technique_family') {
    const isGoal = focus.type === 'goal';
    const fgs = atlas.familyGoals.filter(fg => (isGoal ? fg.goal : fg.family) === id && atlas.nodes[isGoal ? fg.family : fg.goal]);
    if (isGoal) fgs.sort((a, b) => b.attack_count - a.attack_count);
    const other = (fg: typeof fgs[number]) => (isGoal ? fg.family : fg.goal);
    if (fgs.length) out.push({
      key: isGoal ? 'goalFamilies' : 'familyGoals', spec: isGoal ? DERIVED_SPEC.goalFamilies : DERIVED_SPEC.familyGoals,
      ids: fgs.map(other), via: new Map(fgs.map(fg => [other(fg), viaText(fg.attack_count)])),
    });
  }
  return out.sort((a, b) => a.spec.band - b.spec.band);  // stable: REL_SPEC order within a band
}

// Cards per row inside a relation group box.
const colsFor = (n: number, maxCols: number) => Math.max(1, Math.min(maxCols, n <= 2 ? n : n <= 4 ? 2 : 3));

function size(r: Rel, expandedGroups: Set<string>, maxCols: number): Sized {
  const expanded = expandedGroups.has(r.key);
  const capped = r.ids.length > GROUP_CAP;
  // Expanded: the "Show fewer" card keeps its place after the first GROUP_CAP cards and the rest
  // follow it, so the collapse control stays where the user clicked.
  const cells: (string | null)[] = !capped ? r.ids
    : expanded ? [...r.ids.slice(0, GROUP_CAP), null, ...r.ids.slice(GROUP_CAP)]
    : [...r.ids.slice(0, GROUP_CAP), null];
  const cols = colsFor(cells.length, maxCols);
  const rows = Math.ceil(cells.length / cols);
  return {
    ...r, expanded, cells, cols,
    w: cols * CARD_W + (cols - 1) * GAP + PAD * 2,
    h: HEAD + rows * CARD_H + (rows - 1) * GAP + PAD,
  };
}

// One candidate arrangement: the focus card in the middle, groups above it (what it
// serves / belongs to) stacked and centred, groups below it either stacked in one
// centred column or split into two columns. Each group gets its own connector lane
// beside the stack: up groups on the right; down groups on the left or right,
// whichever side has fewer lanes so far. The nearest group gets the innermost lane
// and exits the focus card nearest its edge, so connectors never cross.
function arrange(groups: Sized[], two: boolean, narrow: boolean) {
  const LANE = narrow ? 10 : 16, BASE = narrow ? 10 : 16;
  const above = groups.filter(g => g.spec.band < 0);
  const below = groups.filter(g => g.spec.band > 0);
  const placed: Placed[] = [];
  let y = 0;
  above.forEach((g, i) => { placed.push({ g, x: -g.w / 2, y, side: 1, k: above.length - 1 - i }); y += g.h + VGAP; });
  const fy = y + (above.length ? 8 : 0);
  const y0 = fy + CARD_H + VGAP + 8;
  const lanes = { [-1]: 0, [1]: above.length } as Record<number, number>;
  const colY = { [-1]: y0, [1]: y0 } as Record<number, number>;
  for (const g of below) {
    // two columns: fill the shorter one; one column: balance the lanes on each side
    const side: 1 | -1 = two ? (colY[1] < colY[-1] ? 1 : -1) : (lanes[1] < lanes[-1] ? 1 : -1);
    const gy = two ? colY[side] : Math.max(colY[1], colY[-1]);
    const x = two ? (side < 0 ? -COLGAP / 2 - g.w : COLGAP / 2) : -g.w / 2;
    placed.push({ g, x, y: gy, side, k: side > 0 ? lanes[1] - above.length : lanes[-1] });
    lanes[side]++;
    if (two) colY[side] = gy + g.h + VGAP; else colY[1] = colY[-1] = gy + g.h + VGAP;
  }
  // Lane x: beyond the widest box on that side (per column when split).
  const reach = (side: number, up: boolean) => Math.max(CARD_W / 2, ...placed
    .filter(p => (p.g.spec.band < 0) === up && (up || p.side === side))
    .map(p => (side > 0 ? p.x + p.g.w : -p.x)));
  const edges = placed.map(p => {
    const up = p.g.spec.band < 0;
    const side = p.side;
    const n = placed.filter(q => (q.g.spec.band < 0) === up && q.side === side).length;
    // up exits use the card's top half, down exits its bottom half
    const step = Math.min(12, (CARD_H / 2 - 16) / Math.max(1, n - 1));
    // one centred column: right-hand down lanes sit outside the up lanes, so the two never line up
    const laneK = p.k + (!up && side > 0 && !two ? above.length : 0);
    const laneX = side * (reach(side, up) + BASE + laneK * LANE);
    const exitY = up ? fy + 12 + p.k * step : fy + CARD_H - 12 - p.k * step;
    const headY = p.y + HEAD / 2;
    const boxEdge = side > 0 ? p.x + p.g.w : p.x;
    return { p, points: [{ x: side * CARD_W / 2, y: exitY }, { x: laneX, y: exitY }, { x: laneX, y: headY }, { x: boxEdge, y: headY }] };
  });
  const xs = [-CARD_W / 2, CARD_W / 2, ...placed.flatMap(p => [p.x, p.x + p.g.w]), ...edges.flatMap(e => e.points.map(q => q.x))];
  const ys = [fy, fy + CARD_H, ...placed.flatMap(p => [p.y, p.y + p.g.h])];
  const bw = Math.max(...xs) - Math.min(...xs), bh = Math.max(...ys) - Math.min(...ys);
  return { placed, edges, fy, bw, bh };
}

// Groups over GROUP_CAP show GROUP_CAP cards plus a "+N more" summary card. A
// neighbour in two groups appears in both (each shows one relation); the later
// copy is marked as a duplicate of the earlier group. Among the candidate
// arrangements (1-3 card columns per group, one or two group columns) the one
// that shows the most at the largest zoom wins, as long as its width stays
// readable; `view` is the canvas size in px, so the result is deterministic per size.
export function buildFocus(atlas: Atlas, id: string, expandedGroups: Set<string>, view: { w: number; h: number }): GraphLayout {
  const focus = atlas.nodes[id];
  if (!focus) return { nodes: [], edges: [] };
  const narrow = view.w < 520;
  const rels = relationsOf(atlas, id);
  const nBelow = rels.filter(r => r.spec.band > 0).length;

  let best: ReturnType<typeof arrange> | null = null, bestScore = -Infinity, bestW = Infinity;
  for (const two of nBelow >= 2 && !narrow ? [false, true] : [false]) {
    for (const maxCols of narrow ? [1] : [3, 2, 1]) {
      const a = arrange(rels.map(r => size(r, expandedGroups, maxCols)), two, narrow);
      const fitW = view.w / a.bw;
      const score = fitW >= MIN_FIT ? Math.min(1, fitW, view.h / a.bh) : -Infinity;
      if (score > bestScore + 1e-6 || (bestScore === -Infinity && score === -Infinity && a.bw < bestW)) {
        best = a; bestScore = score; bestW = a.bw;
      }
    }
  }
  const { edges: lanes, fy } = best!;

  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const fx = -CARD_W / 2;
  nodes.push({ id, type: 'card', position: { x: fx, y: fy }, width: CARD_W, height: CARD_H, data: { nodeId: id, focus: true }, ...QUIET });

  const firstGroup = new Map<string, string>();  // neighbour -> label of the first group showing it
  for (const { p, points } of lanes.sort((a, b) => a.p.y - b.p.y)) {
    const g = p.g;
    const boxId = `grp:${g.key}`;
    const conds = g.ids.map(n => conditionOf(atlas, g.spec.type, g.spec.out ? id : n, g.spec.out ? n : id));
    const nCond = conds.filter(Boolean).length;
    const capped = g.ids.length > GROUP_CAP;
    nodes.push({
      id: boxId, type: 'relgroup', position: { x: p.x, y: p.y }, width: g.w, height: g.h,
      selectable: false, focusable: false, zIndex: -1, ...QUIET,
      data: {
        key: g.key, label: g.spec.label, count: g.ids.length, cls: CLASS_OF[g.spec.type], conditional: nCond,
        ...(capped ? { expanded: g.expanded, hidden: g.ids.length - GROUP_CAP } : {}),
      },
    });
    const cell = (i: number) => ({
      x: p.x + PAD + (i % g.cols) * (CARD_W + GAP),
      y: p.y + HEAD + Math.floor(i / g.cols) * (CARD_H + GAP),
    });
    let rank = 0;
    g.cells.forEach((n, i) => {
      if (n === null) {
        nodes.push({
          id: `more:${g.key}`, type: 'summary', position: cell(i), width: CARD_W, height: CARD_H, ...QUIET,
          data: { groupKey: g.key, hidden: g.ids.length - GROUP_CAP, label: g.spec.label, expanded: g.expanded,
            firstHidden: `${g.key}:${g.ids[GROUP_CAP]}` },
        });
        return;
      }
      const j = rank++;
      const also = firstGroup.get(n);
      if (!also) firstGroup.set(n, g.spec.label);
      nodes.push({
        id: `${g.key}:${n}`, type: 'card', position: cell(i), width: CARD_W, height: CARD_H, ...QUIET,
        data: {
          nodeId: n, group: `${g.spec.label}, ${j + 1} of ${g.ids.length}`,
          ...(also ? { also } : {}), ...(conds[j] ? { conditional: conds[j] } : {}),
          ...(g.via?.get(n) ? { via: g.via.get(n) } : {}),
        },
      });
    });

    const allCond = nCond > 0 && nCond === g.ids.length;
    const title = `${g.spec.label} (${g.ids.length})${allCond ? ': conditional, see each card' : ''}`;
    edges.push({
      id: `e:${g.key}`, source: id, target: boxId, type: 'atlas', ariaLabel: title,
      data: {
        points, curve: 'elbow', cls: CLASS_OF[g.spec.type], width: 2,
        // the arrowhead marks the authored direction (source -> target)
        arrow: g.spec.type === 'distinct_from' ? 'none' : g.spec.out ? 'end' : 'start',
        cond: allCond, title,
      },
    });
  }

  // Reading order (arrow keys, screen readers): top to bottom, then left to right.
  nodes.sort((a, b) => a.position.y - b.position.y || a.position.x - b.position.x);
  return { nodes, edges };
}

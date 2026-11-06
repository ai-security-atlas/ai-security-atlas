import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Search, ChevronRight, ChevronDown, X, Moon, Sun, ArrowLeft, ArrowUpRight,
  BookOpen, ExternalLink, Share2, AlertTriangle, FileText, Link2,
  Key, Shield, ScrollText, Layers, List as ListIcon, Compass, Crosshair, PenLine, Home,
  SquareTerminal, Play, CornerUpRight, ChevronsUpDown, ChevronsDownUp,
} from 'lucide-react';

const REPO_URL = 'https://github.com/ai-security-atlas/ai-security-atlas';

// lucide-react dropped brand icons; use the GitHub mark inline.
const GithubMark = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20" aria-hidden="true">
    <path d="M12 .5C5.37.5 0 5.78 0 12.29c0 5.2 3.44 9.6 8.2 11.16.6.1.82-.25.82-.56 0-.28-.01-1.02-.02-2-3.34.72-4.04-1.6-4.04-1.6-.55-1.36-1.33-1.72-1.33-1.72-1.09-.73.08-.72.08-.72 1.2.08 1.84 1.22 1.84 1.22 1.07 1.8 2.8 1.28 3.49.98.1-.76.42-1.28.76-1.57-2.67-.3-5.47-1.31-5.47-5.83 0-1.29.47-2.34 1.23-3.17-.12-.3-.53-1.52.12-3.16 0 0 1-.32 3.3 1.21a11.5 11.5 0 0 1 6 0c2.3-1.53 3.29-1.21 3.29-1.21.65 1.64.24 2.86.12 3.16.77.83 1.23 1.88 1.23 3.17 0 4.53-2.81 5.53-5.49 5.82.43.37.81 1.1.81 2.22 0 1.6-.01 2.9-.01 3.29 0 .31.21.68.83.56A12.3 12.3 0 0 0 24 12.29C24 5.78 18.63.5 12 .5z" />
  </svg>
);
import {
  Atlas, AtlasNode, Lab, PracticedIn, AreaLab, NavSection, loadAtlas, glyphFor, REL_ORDER, OVERVIEW_RELS,
  humanizeToken,
} from './atlas';
// The graph (React Flow) loads on first use: it is hidden by default on desktop and a separate tab on phones.
const GraphView = React.lazy(() => import('./graph/GraphView'));
const graphLoading = <div className="graphwrap graphwrap--loading" role="status">Loading graph…</div>;

// The graph is a lazy chunk; if it fails to load (offline, or a tab left open across a
// deploy that removed the old hashed chunk), only the graph pane shows the error.
class GraphBoundary extends React.Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="graphwrap graphwrap--loading" role="alert">
        <p>The graph failed to load.</p>
        <button className="segbtn" onClick={() => window.location.reload()}>Reload</button>
      </div>
    );
  }
}
// Below 1024px the desktop graph pane overlays the reader, so leaving the graph closes it.
const overlayGraph = () => typeof window !== 'undefined' && !!window.matchMedia?.('(max-width: 1023px)').matches;
const phone = () => typeof window !== 'undefined' && !!window.matchMedia?.('(max-width: 767px)').matches;

/* ------------------------------------------------------------------ helpers */

const useTheme = () => {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'light';
    const stored = localStorage.getItem('theme');
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  useEffect(() => {
    const r = document.documentElement;
    r.classList.toggle('dark', theme === 'dark');
    r.classList.toggle('light', theme === 'light');
    r.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);
  return { theme, toggle: () => setTheme(t => (t === 'dark' ? 'light' : 'dark')) };
};

function TypeIcon({ atlas, type, className }: { atlas: Atlas; type: string; className?: string }) {
  const meta = atlas.typeMeta[type];
  const Glyph = glyphFor(meta?.glyph || 'BookOpen');
  return <Glyph className={className} style={{ color: meta?.color }} />;
}

function accentVar(atlas: Atlas, type: string): React.CSSProperties {
  return { ['--accent' as any]: atlas.typeMeta[type]?.color || 'var(--theme-action)' };
}

/* ------------------------------------------------------------------- chips */

function NodeChip({ atlas, id, onOpen }: { atlas: Atlas; id: string; onOpen: (id: string) => void }) {
  const n = atlas.nodes[id];
  if (!n) return null;
  const Glyph = glyphFor(atlas.typeMeta[n.type]?.glyph || 'BookOpen');
  return (
    <button className="chip" style={accentVar(atlas, n.type)} onClick={() => onOpen(id)} title={n.title}>
      <Glyph />
      <span>{n.title}</span>
    </button>
  );
}

function RelGroup({ atlas, groupKey, ids, onOpen }: {
  atlas: Atlas; groupKey: string; ids: string[]; onOpen: (id: string) => void;
}) {
  if (!ids?.length) return null;
  return (
    <div className="rel">
      <div className="rel__head">
        <h3>{atlas.relLabels[groupKey] || groupKey}</h3>
        <span className="n">{ids.length}</span>
      </div>
      <div className="chips">
        {ids.map(id => <NodeChip key={id} atlas={atlas} id={id} onOpen={onOpen} />)}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- navigation */

// A node "has a lab" when it is a lab's own topic or practiced in another lab's steps.

function NavRow({ atlas, id, active, depth, expandable, expanded, onToggle, onOpen, count, aliasOf }: {
  atlas: Atlas; id: string; active: boolean; depth: number; expandable: boolean;
  expanded: boolean; onToggle: () => void; onOpen: () => void; count?: number;
  aliasOf?: string;  // alias row: the attack's canonical row lives under this goal; never active
}) {
  const n = atlas.nodes[id];
  if (!n) return null;
  const Glyph = glyphFor(atlas.typeMeta[n.type]?.glyph || 'BookOpen');
  const aliasTitle = aliasOf ? `Listed under ${atlas.nodes[aliasOf]?.title || aliasOf}` : undefined;
  return (
    <div className="nav-row" data-active={active} data-alias={aliasOf ? 'true' : undefined} role="button" tabIndex={0}
      aria-label={aliasOf ? `${n.title} (${aliasTitle})` : n.title} aria-current={active ? 'true' : undefined} title={aliasTitle}
      style={{ ...accentVar(atlas, n.type), paddingLeft: `${0.4 + depth * 0.85}rem` }}
      onClick={onOpen}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(); } }}>
      <span className="nav-row__mark" />
      <button
        className={`nav-row__chev ${expandable ? '' : 'nav-row__chev--hidden'}`}
        onClick={e => { e.stopPropagation(); onToggle(); }}
        aria-label={expanded ? 'Collapse' : 'Expand'} tabIndex={-1}
      >
        {expanded ? <ChevronDown /> : <ChevronRight />}
      </button>
      <span className="nav-row__glyph"><Glyph /></span>
      <span className="nav-row__label">{n.title}</span>
      {aliasOf && <span className="nav-row__alias" aria-hidden="true"><CornerUpRight /></span>}
      {n.lab
        ? <span className="nav-row__lab" title={`Hands-on lab · ${n.lab.lab_id}`} aria-label="Has a hands-on lab"><SquareTerminal /></span>
        : n.practiced_in && <span className="nav-row__lab nav-row__lab--lite" title={`Practiced in ${n.practiced_in.lab_id}`} aria-label="Practiced in a lab"><SquareTerminal /></span>}
      {count != null && <span className="nav-row__count">{count}</span>}
    </div>
  );
}

// Sections below the objectives tree, in nav order. Methods and formats fold into
// Foundations as subgroups.
const SECTION_ORDER = ['defenses', 'evaluation', 'foundations'];
const FOLD_INTO_FOUNDATIONS = ['methods', 'formats'];

function navSections(atlas: Atlas): NavSection[] {
  const byId = Object.fromEntries(atlas.nav.sections.map(s => [s.id, s]));
  const folded = FOLD_INTO_FOUNDATIONS.flatMap(id => byId[id]?.groups || []);
  const rest = atlas.nav.sections.filter(s => !SECTION_ORDER.includes(s.id) && !FOLD_INTO_FOUNDATIONS.includes(s.id));
  return [
    ...SECTION_ORDER.map(id => byId[id]).filter(Boolean)
      .map(s => (s.id === 'foundations' ? { ...s, groups: [...s.groups, ...folded] } : s)),
    ...rest,
  ];
}

// Flat technique-family index: every family with its member attacks, by title.
function familyIndex(atlas: Atlas): { id: string; members: string[] }[] {
  return Object.values(atlas.nodes)
    .filter(n => n.type === 'technique_family')
    .sort((a, b) => a.title.localeCompare(b.title))
    .map(n => ({ id: n.id, members: (n.rel?.hasMember || []).filter(id => atlas.nodes[id]?.type === 'attack') }));
}

const SUBGROUP_STYLE: React.CSSProperties = { padding: '0.4rem 0.75rem 0.15rem 1.6rem', fontFamily: 'var(--mono)', fontSize: '0.6rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--theme-muted)', opacity: 0.8 };

function SectionHead({ open, onToggle, glyph: Glyph, label, total }: {
  open: boolean; onToggle: () => void; glyph: any; label: string; total: number;
}) {
  return (
    <button className="nav__section-label" style={{ width: '100%' }} onClick={onToggle} aria-expanded={open}>
      {open ? <ChevronDown /> : <ChevronRight />}<Glyph /> {label}
      <span style={{ marginLeft: 'auto', opacity: 0.7 }}>{total}</span>
    </button>
  );
}

function Sidebar({ atlas, selectedId, onOpen, onHome, search, onSearch, results, expanded, toggle, setExpanded }: {
  atlas: Atlas; selectedId: string | null; onOpen: (id: string) => void; onHome: () => void;
  search: string; onSearch: (e: any) => void; results: any[];
  expanded: Set<string>; toggle: (key: string) => void;
  setExpanded: (keys: Set<string>) => void;
}) {
  const is = (k: string) => expanded.has(k);
  const sections = useMemo(() => navSections(atlas), [atlas]);
  const families = useMemo(() => familyIndex(atlas), [atlas]);
  const objectives = atlas.nav.objectives.map(obj => {
    const fams = obj.families
      .map(f => ({ id: f.id, rows: (f.attacks || f.attackIds.map(id => ({ id, primary: true }))) }))
      .filter(f => f.rows.length > 0);
    const loose = obj.looseAttackIds;
    return { goalId: obj.goalId, fams, loose, count: fams.reduce((a, f) => a + f.rows.length, 0) + loose.length };
  });
  const famRows = families.map(f => ({ id: f.id, count: f.members.length }));

  // Every expandable key in the nav, for the expand/collapse-all control.
  const allKeys = useMemo(() => {
    const keys = ['s:objectives', 's:families', ...sections.map(sec => `s:${sec.id}`)];
    for (const obj of atlas.nav.objectives) {
      keys.push(`g:${obj.goalId}`);
      for (const f of obj.families) keys.push(`g:${obj.goalId}/f:${f.id}`);
    }
    return keys;
  }, [atlas, sections]);
  const allOpen = allKeys.every(k => expanded.has(k));

  // Alias rows (an attack under a goal other than its primary_goal) never take the active highlight.
  const attackRow = (a: { id: string; primary: boolean }, depth: number) => (
    <NavRow key={a.id} atlas={atlas} id={a.id} active={a.primary && selectedId === a.id} depth={depth}
      aliasOf={a.primary ? undefined : atlas.nodes[a.id]?.primary_goal}
      expandable={false} expanded={false} onToggle={() => {}} onOpen={() => onOpen(a.id)} />
  );

  return (
    <>
      <div className="nav__head">
        <button className="nav__brand" onClick={onHome} aria-label="AI Security Atlas — home">
          <Shield className="w-5 h-5" />
          AI Security
          <small>ATLAS</small>
        </button>
        <div className="search">
          <Search />
          <input value={search} onChange={onSearch} placeholder="Search techniques, concepts…" aria-label="Search" />
        </div>
      </div>

      <div className="nav__scroll">
        {search ? (
          <div className="sr">
            {results.map((r, i) => {
              const id = (r.url || '').match(/\/(?:nodes|sources)\/([^/]+)/)?.[1];
              const n = id ? atlas.nodes[id] : null;
              return (
                <div key={i} className="sr__item" style={n ? accentVar(atlas, n.type) : undefined}
                  onClick={() => id && atlas.nodes[id] ? onOpen(id) : (window.location.href = r.url)}>
                  <div className="sr__title">
                    {n && <TypeIcon atlas={atlas} type={n.type} />}
                    {r.meta?.title || n?.title || r.url}
                  </div>
                  {r.excerpt && <div className="sr__excerpt" dangerouslySetInnerHTML={{ __html: r.excerpt }} />}
                </div>
              );
            })}
            {results.length === 0 && <div className="sr__empty">No matches for “{search}”.</div>}
          </div>
        ) : (
          <>
            <div className="nav__tools">
              <button className="nav__toggleall" onClick={() => setExpanded(new Set(allOpen ? [] : allKeys))}
                aria-label={allOpen ? 'Collapse all sections' : 'Expand all sections'} title={allOpen ? 'Collapse all' : 'Expand all'}>
                {allOpen ? <ChevronsDownUp /> : <ChevronsUpDown />}
              </button>
            </div>
            <SectionHead open={is('s:objectives')} onToggle={() => toggle('s:objectives')} glyph={Compass}
              label="Adversary objectives" total={objectives.length} />
            {is('s:objectives') && objectives.map(obj => {
              const gKey = `g:${obj.goalId}`;
              const gOpen = is(gKey);
              return (
                <div key={obj.goalId}>
                  <NavRow atlas={atlas} id={obj.goalId} active={selectedId === obj.goalId} depth={0}
                    expandable={obj.fams.length + obj.loose.length > 0} expanded={gOpen}
                    onToggle={() => toggle(gKey)} onOpen={() => onOpen(obj.goalId)} count={obj.count} />
                  {gOpen && (
                    <div className="nav-children">
                      {obj.fams.map(fam => {
                        const fKey = `${gKey}/f:${fam.id}`;
                        const fOpen = is(fKey);
                        // The family's canonical (active) row is in the Technique families index.
                        return (
                          <div key={fam.id}>
                            <NavRow atlas={atlas} id={fam.id} active={false} depth={1}
                              expandable expanded={fOpen}
                              onToggle={() => toggle(fKey)} onOpen={() => onOpen(fam.id)} count={fam.rows.length} />
                            {fOpen && fam.rows.map(a => attackRow(a, 2))}
                          </div>
                        );
                      })}
                      {obj.loose.map(aid => attackRow({ id: aid, primary: atlas.nodes[aid]?.primary_goal === obj.goalId }, 1))}
                    </div>
                  )}
                </div>
              );
            })}

            {famRows.length > 0 && (
              <>
                <SectionHead open={is('s:families')} onToggle={() => toggle('s:families')}
                  glyph={glyphFor(atlas.typeMeta.technique_family?.glyph || 'Layers')} label="Technique families" total={famRows.length} />
                {is('s:families') && famRows.map(f => (
                  <NavRow key={f.id} atlas={atlas} id={f.id} active={selectedId === f.id} depth={1}
                    expandable={false} expanded={false} onToggle={() => {}} onOpen={() => onOpen(f.id)} count={f.count} />
                ))}
              </>
            )}

            {sections.map(sec => {
              const sKey = `s:${sec.id}`;
              const sOpen = is(sKey);
              const groups = sec.groups.filter(g => g.ids.length > 0);
              const total = groups.reduce((a, g) => a + g.ids.length, 0);
              if (total === 0) return null;
              return (
                <div key={sec.id}>
                  <SectionHead open={sOpen} onToggle={() => toggle(sKey)} glyph={glyphFor(sec.glyph)} label={sec.label} total={total} />
                  {sOpen && groups.map(grp => (
                    <div key={grp.label}>
                      {groups.length > 1 && <div style={SUBGROUP_STYLE}>{grp.label}</div>}
                      {grp.ids.map(id => (
                        <NavRow key={id} atlas={atlas} id={id} active={selectedId === id} depth={1}
                          expandable={false} expanded={false} onToggle={() => {}} onOpen={() => onOpen(id)} />
                      ))}
                    </div>
                  ))}
                </div>
              );
            })}

            <a className="nav__more nav__more--foot" href="/labs/"><SquareTerminal /> Lab catalog →</a>
          </>
        )}
      </div>
    </>
  );
}

/* ---------------------------------------------------------------- landing */

const STEP_TYPES = ['concept', 'architecture', 'component', 'lifecycle', 'method', 'format'];

// "How to read the atlas": one concrete path down the tree, derived from the data
// (first objective -> its family with most canonical attacks -> an attack, lab first -> a control -> a prerequisite).
function readingPath(atlas: Atlas): { step: string; id?: string }[] {
  const obj = atlas.nav.objectives[0];
  const fam = obj && [...obj.families].sort((a, b) => (b.primaryCount || 0) - (a.primaryCount || 0))[0];
  const prim = fam ? (fam.attacks || []).filter(a => a.primary).map(a => a.id) : [];
  const attack = prim.find(id => atlas.nodes[id]?.lab) || prim[0];
  const rel = (attack && atlas.nodes[attack]?.rel) || {};
  return [
    { step: 'Objective', id: obj?.goalId },
    { step: 'Family', id: fam?.id },
    { step: 'Attack', id: attack },
    { step: 'Defense & evaluation', id: (rel.mitigatedBy || [])[0] || (rel.evaluatedBy || [])[0] },
    { step: 'Foundations', id: (rel.requires || []).find(id => STEP_TYPES.includes(atlas.nodes[id]?.type)) },
  ];
}

// Start-here labs: beginner labs in lab-number order, one per primary objective first, then fill.
function startHere(labs: Lab[], max = 6): Lab[] {
  const beginner = labs.filter(l => l.level === 'beginner');
  const seen = new Set<string>();
  const out: Lab[] = [];
  for (const l of beginner) {
    const g = l.objectives?.[0];
    if (out.length < max && g && !seen.has(g)) { seen.add(g); out.push(l); }
  }
  for (const l of beginner) if (out.length < max && !out.includes(l)) out.push(l);
  return out.sort((a, b) => a.number - b.number);
}

const scrollToId = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

function Landing({ atlas, onOpen }: { atlas: Atlas; onOpen: (id: string) => void }) {
  const c = atlas.meta.counts;
  const labs = atlas.labs || [];
  const picks = useMemo(() => startHere(labs), [labs]);
  const path = useMemo(() => readingPath(atlas), [atlas]);
  return (
    <div className="landing">
      <div className="landing__hero">
        <div className="eyb eyb--accent" style={{ ['--accent' as any]: 'var(--theme-action)' }}>
          <span className="type-dot" /> AI SECURITY RESEARCH GRAPH
        </div>
        <h1>An opinionated map of how AI systems are attacked, defended, and evaluated.</h1>
        <p className="landing__lead">
          Start from an adversary objective and descend to the mechanism, its prerequisites,
          the architectures it applies to, the evidence behind it, and the controls that address
          it. Every claim links to a source; the site hosts no exploits, and the local labs use
          only inert canary payloads.
        </p>
        <div className="landing__ctas">
          <button className="herocta" onClick={() => scrollToId('objectives')}>
            <Crosshair /><span><b>Explore the threat map</b><small>Objectives, techniques, defenses</small></span>
          </button>
          {labs.length > 0 && (
            <button className="herocta herocta--lab" onClick={() => scrollToId('start-here')}>
              <SquareTerminal /><span><b>Learn hands-on</b><small>{labs.length} local labs, beginner to advanced</small></span>
            </button>
          )}
        </div>
      </div>

      <div id="objectives" className="eyb landing__anchor" style={{ marginBottom: '1rem' }}><Crosshair style={{ width: '0.85rem', height: '0.85rem' }} /> ADVERSARY OBJECTIVES</div>
      <div className="obj-grid">
        {atlas.nav.objectives.map((obj, i) => {
          const g = atlas.nodes[obj.goalId];
          if (!g) return null;
          const misuse = obj.goalId === 'goal-misuse';
          const nLabs = g.labs_in_area?.filter(r => r.relation !== 'foundation').length || 0;
          const nFound = (g.labs_in_area?.length || 0) - nLabs;
          return (
            <button key={obj.goalId} className={`obj-card ${misuse ? 'obj-card--misuse' : ''}`}
              style={accentVar(atlas, 'goal')} onClick={() => onOpen(obj.goalId)}>
              <div className="obj-card__n">{misuse ? 'ADJACENT LENS' : `OBJECTIVE ${String(i + 1).padStart(2, '0')}`}</div>
              <div className="obj-card__title">{g.title}</div>
              <div className="obj-card__sum">{g.summary}</div>
              <div className="obj-card__foot">
                <span className="obj-card__count">
                  <b>{obj.count}</b> techniques · {obj.families.length} families
                  {labs.length > 0 && <> · <span className="obj-card__labs">{nLabs || !nFound ? `${nLabs} ${nLabs === 1 ? 'lab' : 'labs'}` : ''}{nLabs && nFound ? ' + ' : ''}{nFound ? `${nFound} foundation` : ''}</span></>}
                </span>
                <span className="obj-card__go"><ArrowUpRight style={{ width: '1.1rem', height: '1.1rem' }} /></span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="eyb" style={{ margin: '3rem 0 1rem' }}><Compass style={{ width: '0.85rem', height: '0.85rem' }} /> HOW TO READ THE ATLAS</div>
      <ol className="readpath">
        {path.map(s => {
          const n = s.id ? atlas.nodes[s.id] : null;
          return (
            <li key={s.step} style={n ? accentVar(atlas, n.type) : undefined}>
              <button className="readpath__step" disabled={!n} onClick={() => n && onOpen(n.id)}
                title={n ? `Example: ${n.title}` : undefined}>
                <span className="readpath__k">{s.step}</span>
                {n && <span className="readpath__ex">{n.title}</span>}
              </button>
            </li>
          );
        })}
      </ol>

      {picks.length > 0 && (
        <>
          <div id="start-here" className="eyb landing__anchor" style={{ margin: '3rem 0 1rem' }}><SquareTerminal style={{ width: '0.85rem', height: '0.85rem' }} /> START HERE · BEGINNER LABS</div>
          <div className="obj-grid">
            {picks.map(l => {
              const goal = l.objectives?.[0] ? atlas.nodes[l.objectives[0]] : null;
              return (
                <a key={l.lab_id} className="obj-card obj-card--lab" href={l.page}>
                  <div className="obj-card__n">{l.lab_id} · {goal ? goal.title : 'Foundations'}</div>
                  <div className="obj-card__title">{l.title}</div>
                  <div className="obj-card__sum">
                    Practices <b>{atlas.nodes[l.node]?.title || l.node}</b>
                    {l.model_backend ? ` · ${BACKEND_LABEL[l.model_backend] || l.model_backend}` : ''}
                  </div>
                  <div className="obj-card__foot">
                    <span className="obj-card__count"><b>{l.level}</b> · {l.time}</span>
                    <span className="obj-card__go"><ArrowUpRight style={{ width: '1.1rem', height: '1.1rem' }} /></span>
                  </div>
                </a>
              );
            })}
          </div>
          <a className="landing__all" href="/labs/">All {labs.length} labs →</a>
        </>
      )}

      <div className="landing__stats landing__band">
        <div className="stat"><b>{c.nodes}</b><small>Topics</small></div>
        <div className="stat"><b>{c.edges}</b><small>Relationships</small></div>
        <div className="stat"><b>{c.sources}</b><small>Sources</small></div>
        <div className="stat"><b>{c.types.attack}</b><small>Attacks</small></div>
        <div className="stat"><b>{c.types.defense}</b><small>Defenses</small></div>
        {!!c.labs && <div className="stat"><b>{c.labs}</b><small>Hands-on labs</small></div>}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- reader */

function GoalFamilies({ atlas, goalId, onOpen }: { atlas: Atlas; goalId: string; onOpen: (id: string) => void }) {
  const obj = atlas.nav.objectives.find(o => o.goalId === goalId);
  if (!obj) return null;
  return (
    <>
      {obj.families.map(fam => {
        const f = atlas.nodes[fam.id];
        return (
          <div key={fam.id} className="famblock" style={accentVar(atlas, 'technique_family')}>
            <div className="famblock__head">
              <TypeIcon atlas={atlas} type="technique_family" />
              <button className="t" onClick={() => onOpen(fam.id)} style={{ cursor: 'pointer' }}>{f?.title || fam.id}</button>
              <span className="rel__head" style={{ marginLeft: 'auto' }}><span className="n">{fam.attackIds.length}</span></span>
            </div>
            <div className="chips">
              {fam.attackIds.map(aid => <NodeChip key={aid} atlas={atlas} id={aid} onOpen={onOpen} />)}
            </div>
          </div>
        );
      })}
      {obj.looseAttackIds.length > 0 && (
        <div className="rel">
          <div className="rel__head"><h3>Other techniques</h3><span className="n">{obj.looseAttackIds.length}</span></div>
          <div className="chips">{obj.looseAttackIds.map(aid => <NodeChip key={aid} atlas={atlas} id={aid} onOpen={onOpen} />)}</div>
        </div>
      )}
    </>
  );
}

// Renders the authored article body by fetching the Hugo-rendered fragment
// (PRD 10.3: reuse the same-origin HTML, don't re-render Markdown client-side).
function ArticleBody({ id, onOpen }: { id: string; onOpen: (id: string) => void }) {
  const [html, setHtml] = useState<string | null>(null);
  const [status, setStatus] = useState<'loading' | 'ok' | 'none'>('loading');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading'); setHtml(null);
    fetch(`/nodes/${id}/`, { cache: 'no-cache' })
      .then(r => (r.ok ? r.text() : Promise.reject()))
      .then(txt => {
        if (cancelled) return;
        const doc = new DOMParser().parseFromString(txt, 'text/html');
        const el = doc.querySelector('[data-article-body]');
        if (el && el.textContent && el.textContent.trim()) { setHtml(el.innerHTML); setStatus('ok'); }
        else setStatus('none');
      })
      .catch(() => { if (!cancelled) setStatus('none'); });
    return () => { cancelled = true; };
  }, [id]);

  // Keep in-article links inside the SPA.
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement).closest('a');
      if (!a) return;
      const m = (a.getAttribute('href') || '').match(/^\/nodes\/([^/]+)\/(?:(?:labs|evidence|relationships)\/)?$/);
      if (m) { e.preventDefault(); onOpen(m[1]); }
    };
    root.addEventListener('click', onClick);
    return () => root.removeEventListener('click', onClick);
  }, [html, onOpen]);

  if (status === 'none') return null;
  if (status === 'loading') return <div className="prose" style={{ opacity: 0.4, fontSize: '0.9rem' }}>Loading overview…</div>;
  return (
    <div style={{ marginBottom: '2rem' }}>
      <div className="draft-note"><PenLine /> AI-generated draft · conceptual overview, not yet reviewed</div>
      <div className="prose" ref={ref} dangerouslySetInnerHTML={{ __html: html! }} />
    </div>
  );
}

const BACKEND_LABEL: Record<string, string> = {
  none: 'no model backend', optional: 'model backend optional', required: 'model backend required',
};

const ROADMAP_URL = `${REPO_URL}/blob/main/docs/labs-roadmap.md`;

// Hands-on lab panel: links to the lab page (explainer + guide, same tab) and the lab folder on GitHub.
function LabCard({ lab }: { lab: Lab }) {
  return (
    <section className="labcard" aria-label={`Hands-on lab ${lab.lab_id}`}>
      <div className="eyb eyb--lab"><SquareTerminal /> Hands-on lab · {lab.lab_id}</div>
      <div className="labcard__title">{lab.title}</div>
      <div className="labcard__meta">
        {lab.level && <span>{lab.level}</span>}
        {lab.time && <span>{lab.time}</span>}
        {lab.model_backend && <span>{BACKEND_LABEL[lab.model_backend] || lab.model_backend}</span>}
      </div>
      <p className="labcard__body">
        Reproduce this mechanism on your own machine in Docker. Every step ends in a harmless canary,
        and the lab closes with a defense chapter.
      </p>
      <div className="labcard__actions">
        <a className="labbtn labbtn--primary" href={lab.page}><Play /> Open lab</a>
        {lab.explainer && <a className="labbtn" href={`${lab.page}#lab-explainer`}><Compass /> Explainer</a>}
        <a className="labbtn" href={`${lab.page}#lab-guide`}><BookOpen /> Guide</a>
        <a className="labbtn" href={lab.github} target="_blank" rel="noreferrer"><GithubMark /> GitHub</a>
      </div>
    </section>
  );
}

// Compact one-line lab call to action above the tabs, for a node with its own lab.
function LabStrip({ lab }: { lab: Lab }) {
  return (
    <a className="labstrip" href={lab.page} aria-label={`Open hands-on lab ${lab.lab_id}: ${lab.title}`}>
      <SquareTerminal />
      <b>{lab.lab_id}</b>
      {lab.level && <span>{lab.level}</span>}
      {lab.time && <span>{lab.time}</span>}
      <span className="labstrip__go">Open lab <ArrowUpRight /></span>
    </a>
  );
}

const stepsLabel = (steps: string) => `${/[,-]/.test(steps) ? 'Steps' : 'Step'} ${steps}`;

// Lighter twin of LabCard for a node practiced inside another lab's steps.
function PracticedCard({ atlas, p, onOpen }: { atlas: Atlas; p: PracticedIn; onOpen: (id: string) => void }) {
  return (
    <section className="labcard labcard--lite" aria-label={`Practiced in ${p.lab_id}`}>
      <a className="eyb eyb--lab labcard__steps" href={p.url}>
        <SquareTerminal /><span>Practiced in {p.lab_id}</span><span>· {stepsLabel(p.steps)} <ArrowUpRight /></span>
      </a>
      <p className="labcard__body">
        This topic has no lab of its own. You practice it in those steps of{' '}
        <a className="labcard__link" href={p.url.split('#')[0]}>{p.lab_id} · {p.title}</a>
        {atlas.nodes[p.node] && <> (<button className="labarea__topic" onClick={() => onOpen(p.node)}>{atlas.nodes[p.node].title}</button>)</>}.
      </p>
    </section>
  );
}

const REL_MARK: Record<string, { label: string; hint: string }> = {
  own: { label: 'own', hint: "The lab's own topic is in this area" },
  practiced: { label: 'practiced', hint: "The lab's steps practice a topic in this area" },
  foundation: { label: 'foundation', hint: 'Background lab, placed here through the attacks its topic links to' },
};

// Hub nodes (goals, families, umbrellas): the labs that practice their members, grouped by family.
function LabsInArea({ atlas, hubId, rows, onOpen }: { atlas: Atlas; hubId: string; rows: AreaLab[]; onOpen: (id: string) => void }) {
  const groups = new Map<string, AreaLab[]>();
  rows.forEach(r => groups.set(r.family || '', [...(groups.get(r.family || '') || []), r]));
  const keys = [...groups.keys()].sort((a, b) => (atlas.nodes[a]?.title || '~').localeCompare(atlas.nodes[b]?.title || '~'));
  return (
    <section className="labcard labcard--lite" aria-label="Labs in this area">
      <div className="eyb eyb--lab"><SquareTerminal /> Labs in this area · {rows.length}</div>
      {keys.map(k => (
        <div key={k || 'none'} className="labgroup">
          {k !== hubId && (
            <div className="labgroup__head">
              {atlas.nodes[k]
                ? <button className="labarea__topic" onClick={() => onOpen(k)}>{atlas.nodes[k].title}</button>
                : 'Other'}
            </div>
          )}
          <ul className="labarea">
            {groups.get(k)!.map(r => (
              <li key={r.lab_id}>
                <span className="labrel" data-rel={r.relation} title={REL_MARK[r.relation]?.hint}>{REL_MARK[r.relation]?.label || r.relation}</span>
                <a className="labcard__link" href={r.page}>{r.lab_id} · {r.title}</a>
                <span className="labarea__meta">
                  {(r.level || r.time) && <span>{[r.level, r.time].filter(Boolean).join(' · ')}</span>}
                  {r.relation !== 'practiced' && atlas.nodes[r.node] && (
                    <button className="labarea__topic" onClick={() => onOpen(r.node)}>{atlas.nodes[r.node].title}</button>
                  )}
                  {r.practiced.map(pr => (
                    <a key={pr.node} href={pr.url}>
                      {atlas.nodes[pr.node]?.title || pr.node} · {stepsLabel(pr.steps)}
                    </a>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
      <p className="labcard__legend">
        {Object.entries(REL_MARK).map(([k, m]) => (
          <span key={k}><span className="labrel" data-rel={k}>{m.label}</span> {m.hint.toLowerCase()}</span>
        ))}
      </p>
    </section>
  );
}

// Roadmap labs that are not built yet: this node's own planned lab, a planned lab that
// will cover it, and (on hubs) planned labs for the area. Titles only; no page exists.
function PlannedLabs({ atlas, node, onOpen }: { atlas: Atlas; node: AtlasNode; onOpen: (id: string) => void }) {
  const area = node.labs_planned_in_area || [];
  const own = node.planned_lab;
  const pp = node.planned_practiced_in;
  if (!own && !pp && area.length === 0) return null;
  return (
    <section className="labcard labcard--lite labcard--planned" aria-label="Planned labs">
      <div className="eyb"><SquareTerminal /> Planned · {(own ? 1 : 0) + (pp ? 1 : 0) + area.length}</div>
      <ul className="labarea">
        {own && (
          <li>
            <span className="labrel" data-rel="own">own</span>
            <span className="labarea__title">{own.title}</span>
            <span className="labarea__meta">{own.effort && <span>effort {own.effort}</span>}</span>
          </li>
        )}
        {pp && (
          <li>
            <span className="labrel" data-rel="practiced">practiced</span>
            <span className="labarea__title">{pp.title}</span>
            <span className="labarea__meta">{pp.where && <span>{pp.where}</span>}</span>
          </li>
        )}
        {area.map(r => (
          <li key={`${r.node}:${r.title}`}>
            <span className="labrel" data-rel={r.relation}>{REL_MARK[r.relation]?.label || r.relation}</span>
            <span className="labarea__title">{r.title}</span>
            <span className="labarea__meta">
              {atlas.nodes[r.node] && <button className="labarea__topic" onClick={() => onOpen(r.node)}>{atlas.nodes[r.node].title}</button>}
              {r.effort && <span>effort {r.effort}</span>}
            </span>
          </li>
        ))}
      </ul>
      <p className="labcard__body">
        On the <a href={ROADMAP_URL} target="_blank" rel="noreferrer">labs roadmap</a>; not built yet.
      </p>
    </section>
  );
}

// Built labs attached to a node: its own lab, the lab that practices it, and (hubs) labs in the area.
const labCountOf = (n: AtlasNode) => (n.lab ? 1 : 0) + (n.practiced_in ? 1 : 0) + (n.labs_in_area?.length || 0);

function LabsTab({ atlas, node, onOpen }: { atlas: Atlas; node: AtlasNode; onOpen: (id: string) => void }) {
  const planned = !!(node.planned_lab || node.planned_practiced_in || node.labs_planned_in_area?.length);
  return (
    <div className="labtab">
      {node.lab && <LabCard lab={node.lab} />}
      {node.practiced_in && <PracticedCard atlas={atlas} p={node.practiced_in} onOpen={onOpen} />}
      {node.labs_in_area && node.labs_in_area.length > 0 && <LabsInArea atlas={atlas} hubId={node.id} rows={node.labs_in_area} onOpen={onOpen} />}
      {labCountOf(node) === 0 && (
        <div className="labempty">
          <p><b>No lab covers this yet.</b>{planned ? ' One is planned; see below.' : ''}</p>
          <p>
            <a href="/labs/">Browse the lab catalog</a>
            {' · '}
            <a href={ROADMAP_URL} target="_blank" rel="noreferrer">See the labs roadmap</a>
          </p>
        </div>
      )}
      <PlannedLabs atlas={atlas} node={node} onOpen={onOpen} />
    </div>
  );
}

type Tab = 'overview' | 'labs' | 'evidence' | 'map';
const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' }, { id: 'labs', label: 'Labs' },
  { id: 'evidence', label: 'Evidence' }, { id: 'map', label: 'Relationships' },
];

// Reader in the URL: /nodes/<id>/ (overview) and /nodes/<id>/labs|evidence|relationships/.
// Hugo writes a page for each (json2hugo.py NODE_TABS), so every URL also loads directly.
const TAB_PARAM: Record<Tab, string> = { overview: '', labs: 'labs', evidence: 'evidence', map: 'relationships' };
const tabFromParam = (v: string | null | undefined): Tab =>
  (Object.keys(TAB_PARAM) as Tab[]).find(t => v && TAB_PARAM[t] === v) || 'overview';
const nodeURL = (id: string, t: Tab) => `/nodes/${id}/${TAB_PARAM[t] ? `${TAB_PARAM[t]}/` : ''}`;
const NODE_PATH = /^\/nodes\/([a-z0-9-]+)\/(?:(labs|evidence|relationships)\/)?$/;
// The node and tab in the current URL. Old /?node=&tab= links are redirected before the app
// loads (layouts/partials/legacy-redirect.html); reading them here is a fallback.
function routeFromLocation(): { id: string | null; tab: Tab } {
  const m = window.location.pathname.match(NODE_PATH);
  if (m) return { id: m[1], tab: tabFromParam(m[2]) };
  const p = new URLSearchParams(window.location.search);
  return { id: p.get('node'), tab: tabFromParam(p.get('tab')) };
}
// The graph's history entries carry { graph: true } in history.state (it used to be ?view=graph).
const graphEntry = () => !!(history.state && history.state.graph) || new URLSearchParams(window.location.search).get('view') === 'graph';

function Reader({ atlas, node, tab, setTab, onOpen, onGraph }: {
  atlas: Atlas; node: AtlasNode; tab: Tab; setTab: (t: Tab) => void;
  onOpen: (id: string) => void; onGraph: () => void;
}) {
  const meta = atlas.typeMeta[node.type];
  const rel = node.rel || {};
  const overviewKeys = (OVERVIEW_RELS[node.type] || REL_ORDER).filter(k => rel[k]?.length);
  const allRelKeys = REL_ORDER.filter(k => rel[k]?.length);

  // Evidence counts
  const sources = node.references.map(id => atlas.sources[id]).filter(Boolean);
  const access = node.access_profile_ids.map(id => atlas.accessProfiles[id]).filter(Boolean);
  const evCount = sources.length + node.observations.length + node.frameworks.length + access.length;
  const relCount = allRelKeys.reduce((a, k) => a + rel[k].length, 0);
  const labCount = labCountOf(node);

  const isGoal = node.type === 'goal';

  return (
    <div className="reader" style={accentVar(atlas, node.type)}>
      <div className="reader__eyebrow">
        <span className="eyb eyb--accent"><span className="type-dot" /> {meta?.label || node.type}</span>
        {node.evidence_status && <span className="badge badge--ev"><ScrollText />{humanizeToken(node.evidence_status)}</span>}
        {node.content_status && <span className="badge">{node.content_status}</span>}
        {node.priority && <span className="badge">{node.priority}</span>}
        {node.lab && <span className="badge badge--lab"><SquareTerminal />Hands-on lab</span>}
        {node.practiced_in && <span className="badge badge--lab badge--lite"><SquareTerminal />Practiced in {node.practiced_in.lab_id}</span>}
      </div>

      <h1>{node.title}</h1>

      {node.aliases?.length > 0 && (
        <div className="aliases">{node.aliases.map(a => <span key={a} className="alias">{a}</span>)}</div>
      )}

      {node.caveat && (
        <div className="caveat"><AlertTriangle /><p>{node.caveat}</p></div>
      )}

      {node.summary && <p className="summary">{node.summary}</p>}

      {node.lab && <LabStrip lab={node.lab} />}

      {/* WAI-ARIA tabs: roving tabindex, arrow keys / Home / End move and select. */}
      <div className="tabs" role="tablist" onKeyDown={e => {
        const i = TABS.findIndex(x => x.id === tab);
        const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key];
        if (j === undefined) return;
        e.preventDefault();
        const t = TABS[(j + TABS.length) % TABS.length].id;
        setTab(t);
        document.getElementById(`tab-${t}`)?.focus();
      }}>
        {TABS.map(({ id, label }) => {
          const n = { overview: undefined, labs: labCount, evidence: evCount, map: relCount }[id];
          return (
            <button key={id} id={`tab-${id}`} className="tab" role="tab" aria-selected={tab === id} aria-controls="reader-panel"
              tabIndex={tab === id ? 0 : -1} data-on={tab === id} onClick={() => setTab(id)}>
              {label}{n !== undefined && <span className="tab__n">{n}</span>}
            </button>
          );
        })}
      </div>

      <div id="reader-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
      {tab === 'labs' && <LabsTab atlas={atlas} node={node} onOpen={onOpen} />}

      {tab === 'overview' && (
        <>
          {node.has_article && <ArticleBody id={node.id} onOpen={onOpen} />}
          {node.has_article && (isGoal || overviewKeys.length > 0) && <div className="section-title" style={{ marginTop: 0 }}>Connections</div>}
          {isGoal && <GoalFamilies atlas={atlas} goalId={node.id} onOpen={onOpen} />}
          {!isGoal && overviewKeys.map(k => <RelGroup key={k} atlas={atlas} groupKey={k} ids={rel[k]} onOpen={onOpen} />)}
          {!isGoal && !node.has_article && overviewKeys.length === 0 && (
            <p style={{ color: 'var(--theme-muted)', fontSize: '0.9rem' }}>
              This is a seed entry: it carries a definition and routing metadata. See the Relationships and Evidence tabs for its connections and sources.
            </p>
          )}
          <button className="readmore desktop-only" style={{ background: 'transparent', color: 'var(--theme-ink)' }} onClick={onGraph}>
            <Share2 /> Focus in graph
          </button>
        </>
      )}

      {tab === 'evidence' && (
        <>
          {sources.length > 0 && <div className="section-title">Sources · {sources.length}</div>}
          {sources.map(s => (
            <a key={s.id} className="card card--link" href={s.url} target="_blank" rel="noreferrer">
              <span className="ic"><Link2 /></span>
              <div>
                <div className="card__title">{s.title}</div>
                <div className="card__meta">
                  {s.year && <span>{s.year}</span>}
                  {s.kind && <span>{humanizeToken(s.kind)}</span>}
                  {s.publisher && <span>{s.publisher}</span>}
                  {s.verification_depth && <span className="vd">{humanizeToken(s.verification_depth)}</span>}
                </div>
              </div>
            </a>
          ))}

          {node.observations.length > 0 && <div className="section-title">Observations · {node.observations.length}</div>}
          {node.observations.map((o, i) => (
            <div key={o.id || i} className="card">
              <div className="card__title">Target: {o.target_label || 'unspecified'}</div>
              {o.claim && <div className="card__body">{o.claim}</div>}
              <div className="card__meta">
                {o.verification_depth && <span className="vd">{humanizeToken(o.verification_depth)}</span>}
                <span>{o.reproduced ? 'reproduced' : 'not reproduced'}</span>
              </div>
              {o.limitations && <div className="card__limit">{o.limitations}</div>}
            </div>
          ))}

          {access.length > 0 && <div className="section-title">Access profiles · {access.length}</div>}
          {access.map(ap => (
            <div key={ap.id} className="card">
              <div className="card__title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Key style={{ width: '0.9rem', height: '0.9rem', color: 'var(--accent)' }} />{ap.title}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
                {ap.all_of.map(t => <span key={t} className="acap">{humanizeToken(t)}</span>)}
                {ap.any_of.map(t => <span key={t} className="acap">any: {humanizeToken(t)}</span>)}
                {ap.not_required.map(t => <span key={t} className="acap acap--not">{humanizeToken(t)}</span>)}
              </div>
              {ap.caveat && <div className="card__limit">{ap.caveat}</div>}
            </div>
          ))}

          {node.frameworks.length > 0 && <div className="section-title">Framework mappings · {node.frameworks.length}</div>}
          {node.frameworks.map((f, i) => (
            <div key={i} className="card" style={{ display: 'flex', gap: '0.7rem' }}>
              <span className="ic"><FileText style={{ width: '1rem', height: '1rem', color: 'var(--theme-muted)' }} /></span>
              <div>
                <div className="card__title">{f.framework}{f.edition ? ` · ${f.edition}` : ''}</div>
                <div className="card__body">{f.external_id}: {f.title}</div>
              </div>
            </div>
          ))}

          {evCount === 0 && <p style={{ color: 'var(--theme-muted)', fontSize: '0.9rem' }}>No evidence records attached to this entry yet.</p>}
        </>
      )}

      {tab === 'map' && (
        <>
          {allRelKeys.length === 0 && <p style={{ color: 'var(--theme-muted)', fontSize: '0.9rem' }}>No typed relationships recorded.</p>}
          {allRelKeys.map(k => <RelGroup key={k} atlas={atlas} groupKey={k} ids={rel[k]} onOpen={onOpen} />)}
        </>
      )}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------- app */

export function GraphApp() {
  const [atlas, setAtlas] = useState<Atlas | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [trail, setTrail] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>('overview');
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphFull, setGraphFull] = useState(false);
  const [graphNonce, setGraphNonce] = useState(0);  // "Focus in graph": re-sync the graph to the reader
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(['s:objectives']));
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [mobileTab, setMobileTab] = useState<'home' | 'index' | 'graph'>('home');
  const { theme, toggle } = useTheme();

  // --- load atlas ---
  useEffect(() => { loadAtlas().then(setAtlas).catch(e => console.error(e)); }, []);

  // --- pagefind ---
  useEffect(() => {
    (async () => {
      if (typeof window !== 'undefined' && !(window as any).pagefind) {
        try {
          const pf = await import(/* @vite-ignore */ '/pagefind/pagefind.js');
          await pf.options?.({ baseUrl: '/' });
          await pf.init?.();
          (window as any).pagefind = pf;
        } catch { /* fallback to in-memory */ }
      }
    })();
  }, []);

  const expandAncestors = useCallback((id: string, a: Atlas) => {
    // Expand the nav so the selected node is revealed under an objective/section.
    setExpanded(prev => {
      const next = new Set(prev);
      const n = a.nodes[id];
      if (!n) return next;
      if (n.type === 'goal') { next.add('s:objectives'); next.add(`g:${id}`); }
      if (n.type === 'technique_family') next.add('s:families');
      // An attack opens only its primary-goal path; alias rows under other goals stay as they are.
      for (const obj of a.nav.objectives) {
        if (n.primary_goal && obj.goalId !== n.primary_goal) continue;
        const fam = obj.families.find(f => f.attackIds.includes(id));
        if (fam) { next.add('s:objectives'); next.add(`g:${obj.goalId}`); next.add(`g:${obj.goalId}/f:${fam.id}`); break; }
        if (obj.looseAttackIds.includes(id)) { next.add('s:objectives'); next.add(`g:${obj.goalId}`); break; }
      }
      for (const sec of navSections(a)) {
        if (sec.groups.some(g => g.ids.includes(id))) next.add(`s:${sec.id}`);
      }
      return next;
    });
  }, []);

  const open = useCallback((id: string, opts: { push?: boolean; tab?: Tab } = {}) => {
    if (!atlas || !atlas.nodes[id]) return;
    // Re-opening the node already shown (e.g. its own or alias nav row) keeps the tab and adds no history entry.
    const same = id === selectedId && !opts.tab;
    const t = opts.tab || (same ? tab : 'overview');
    setSelectedId(id);
    setTab(t);
    setTrail(prev => opts.push ? [...prev.filter(x => x !== id), id] : [id]);
    expandAncestors(id, atlas);
    setMobileTab('home');
    setSearch(''); setResults([]);
    // From the phone graph tab (a graph history entry) always push, so Back returns to the graph.
    if (!same || graphEntry()) try { history.pushState({ id }, '', nodeURL(id, t)); } catch {}
    document.querySelector('.stage__reader')?.scrollTo({ top: 0 });
  }, [atlas, expandAncestors, selectedId, tab]);

  // Switching tabs rewrites the current history entry, so back/forward return to the tab last shown.
  const changeTab = useCallback((t: Tab) => {
    setTab(t);
    if (selectedId) try { history.replaceState({ id: selectedId }, '', nodeURL(selectedId, t)); } catch {}
  }, [selectedId]);

  // Chip / in-reader navigation pushes to the trail.
  const openLink = useCallback((id: string) => open(id, { push: true }), [open]);

  // The tab title follows the reader, as each /nodes/<id>/ page's own <title> does.
  useEffect(() => {
    const n = atlas && selectedId ? atlas.nodes[selectedId] : null;
    document.title = n ? `${n.title} · AI Security Atlas` : 'AI Security Atlas · AI attack, defense & evaluation knowledge graph';
  }, [atlas, selectedId]);

  // --- URL restore + back/forward ---
  useEffect(() => {
    if (!atlas) return;
    const applyFromURL = () => {
      const { id, tab: t } = routeFromLocation();
      const graph = graphEntry();
      if (id && atlas.nodes[id]) { setSelectedId(id); setTab(t); setTrail([id]); expandAncestors(id, atlas); }
      else setSelectedId(null);
      setMobileTab(graph && phone() ? 'graph' : 'home');
      if (graph && !phone()) setGraphOpen(true);
    };
    applyFromURL();
    const onPop = () => applyFromURL();
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [atlas, expandAncestors]);

  // --- search ---
  const onSearch = useCallback(async (e: any) => {
    const q = e.target.value;
    setSearch(q);
    if (!q) { setResults([]); return; }
    const pf = (window as any).pagefind;
    if (pf) {
      try {
        const sd = await pf.search(q);
        const data = await Promise.all(sd.results.slice(0, 20).map((r: any) => r.data()));
        setResults(data);
        return;
      } catch { /* fall through */ }
    }
    if (atlas) {
      const ql = q.toLowerCase();
      setResults(
        Object.values(atlas.nodes)
          .filter(n => n.title.toLowerCase().includes(ql) || n.aliases.some(a => a.toLowerCase().includes(ql)) || n.summary.toLowerCase().includes(ql))
          .slice(0, 25)
          .map(n => ({ url: `/nodes/${n.id}/`, meta: { title: n.title }, excerpt: n.summary }))
      );
    }
  }, [atlas]);

  const toggleKey = useCallback((k: string) => {
    setExpanded(prev => { const n = new Set(prev); n.has(k) ? n.delete(k) : n.add(k); return n; });
  }, []);

  // Desktop graph pane: leaving the graph (Open, list) exits full screen, and closes the
  // pane where it overlays the reader. Stable callbacks keep the graph's cards from re-rendering.
  const leaveGraph = useCallback(() => { setGraphFull(false); if (overlayGraph()) setGraphOpen(false); }, []);
  // Where the pane overlays the reader, Open closes it: mark the current entry as a graph entry
  // first, so Back reopens the graph (applyFromURL handles graph entries on desktop).
  const markGraphEntry = useCallback(() => {
    if (!overlayGraph() || graphEntry()) return;
    try { history.replaceState({ ...history.state, graph: true }, '', window.location.href); } catch {}
  }, []);
  const graphOpenNode = useCallback((id: string) => { markGraphEntry(); leaveGraph(); openLink(id); }, [markGraphEntry, leaveGraph, openLink]);
  const graphList = useCallback((id: string) => { markGraphEntry(); leaveGraph(); open(id, { push: true, tab: 'map' }); }, [markGraphEntry, leaveGraph, open]);
  const toggleGraphFull = useCallback(() => setGraphFull(v => !v), []);

  const goHome = useCallback(() => {
    setSelectedId(null); setTrail([]); setGraphFull(false); setMobileTab('home');
    setSearch(''); setResults([]);
    try { history.pushState({}, '', '/'); } catch {}
  }, []);

  // Phone graph tab: its own history entry, so Back from the reader (after Open) returns to it.
  const openGraphTab = () => {
    setMobileTab('graph');
    if (graphEntry()) return;
    try { history.pushState({ ...history.state, graph: true }, '', window.location.href); } catch {}
  };

  // Record the graph's focus on the graph tab's entry first, so Back restores it.
  const markGraphTab = (id: string) => {
    if (graphEntry()) try { history.replaceState({ ...history.state, id }, '', nodeURL(id, 'overview')); } catch {}
  };
  const openFromGraphTab = (id: string) => { markGraphTab(id); open(id); };
  const listFromGraphTab = (id: string) => { markGraphTab(id); open(id, { tab: 'map' }); };

  if (!atlas) {
    return <div className="atlas"><div className="empty"><div className="empty__box"><Shield className="big" /><h2>Loading the atlas…</h2></div></div></div>;
  }

  const node = selectedId ? atlas.nodes[selectedId] : null;
  const showGraph = graphOpen || graphFull;

  return (
    <div className="atlas">
      {/* NAV */}
      <aside className="nav" data-mobile-hidden={mobileTab !== 'index'}>
        <Sidebar atlas={atlas} selectedId={selectedId} onOpen={open} onHome={goHome} search={search} onSearch={onSearch}
          results={results} expanded={expanded} toggle={toggleKey} setExpanded={setExpanded} />
      </aside>

      {/* MAIN */}
      <div className="main" data-mobile-hidden={mobileTab === 'index'}>
        <div className="topbar">
          <div className="topbar__left">
            <button className="iconbtn mobile-only" onClick={() => setMobileTab('index')} aria-label="Browse index"><ListIcon /></button>
            <div className="crumbs">
              <button onClick={goHome}>Atlas</button>
              {trail.length > 0 && <span className="sep">/</span>}
              {trail.map((id, i) => (
                <React.Fragment key={id}>
                  {i > 0 && <span className="sep">/</span>}
                  {i === trail.length - 1
                    ? <span className="cur">{atlas.nodes[id]?.title}</span>
                    : <button onClick={() => { setTrail(trail.slice(0, i + 1)); setSelectedId(id); }}>{atlas.nodes[id]?.title}</button>}
                </React.Fragment>
              ))}
            </div>
          </div>
          <div className="topbar__actions">
            <button className="segbtn desktop-only" data-on={graphOpen} onClick={() => { setGraphOpen(v => !v); setGraphFull(false); }}>
              <Share2 /> {graphOpen ? 'Hide graph' : 'Graph'}
            </button>
            <button className="iconbtn" onClick={toggle} aria-label="Toggle theme">
              {theme === 'light' ? <Moon /> : <Sun />}
            </button>
            <a className="iconbtn" href={REPO_URL} target="_blank" rel="noreferrer"
              aria-label="Source & contributions on GitHub" title="Source & contributions on GitHub">
              <GithubMark />
            </a>
          </div>
        </div>

        {/* mobile graph tab shows full graph */}
        {mobileTab === 'graph' ? (
          <div className="stage"><div className="stage__graph">
            <GraphBoundary><React.Suspense fallback={graphLoading}>
              <GraphView atlas={atlas} focusId={selectedId} onOpen={openFromGraphTab} onList={listFromGraphTab} theme={theme} compact />
            </React.Suspense></GraphBoundary>
          </div></div>
        ) : (
          <div className={`stage ${graphFull ? 'stage--graphonly' : ''}`}>
            <div className="stage__reader">
              {node
                ? <Reader atlas={atlas} node={node} tab={tab} setTab={changeTab} onOpen={openLink} onGraph={() => { setGraphOpen(true); setGraphNonce(n => n + 1); }} />
                : <Landing atlas={atlas} onOpen={open} />}
            </div>
            {showGraph && (
              <div className="stage__graph desktop-only">
                <GraphBoundary><React.Suspense fallback={graphLoading}>
                  <GraphView atlas={atlas} focusId={selectedId} focusNonce={graphNonce} theme={theme}
                    onOpen={graphOpenNode} onList={graphList} full={graphFull} onToggleFull={toggleGraphFull} />
                </React.Suspense></GraphBoundary>
              </div>
            )}
          </div>
        )}
      </div>

      {/* MOBILE TAB BAR */}
      <nav className="mtabbar">
        <button className="mtab" data-on={mobileTab === 'home' && !selectedId} onClick={goHome}><Home /> Home</button>
        <button className="mtab" data-on={mobileTab === 'index'} onClick={() => setMobileTab('index')}><ListIcon /> Index</button>
        <button className="mtab" data-on={mobileTab === 'graph'} onClick={openGraphTab}><Share2 /> Graph</button>
      </nav>
    </div>
  );
}

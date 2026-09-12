import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import {
  Search, ChevronRight, ChevronDown, X, Moon, Sun, ArrowLeft, ArrowUpRight,
  BookOpen, ExternalLink, Share2, Maximize2, AlertTriangle, FileText, Link2,
  Key, Shield, ScrollText, Layers, List as ListIcon, Compass, Crosshair, PenLine, Home,
} from 'lucide-react';

const REPO_URL = 'https://github.com/ai-security-atlas/ai-security-atlas';

// lucide-react dropped brand icons; use the GitHub mark inline.
const GithubMark = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20" aria-hidden="true">
    <path d="M12 .5C5.37.5 0 5.78 0 12.29c0 5.2 3.44 9.6 8.2 11.16.6.1.82-.25.82-.56 0-.28-.01-1.02-.02-2-3.34.72-4.04-1.6-4.04-1.6-.55-1.36-1.33-1.72-1.33-1.72-1.09-.73.08-.72.08-.72 1.2.08 1.84 1.22 1.84 1.22 1.07 1.8 2.8 1.28 3.49.98.1-.76.42-1.28.76-1.57-2.67-.3-5.47-1.31-5.47-5.83 0-1.29.47-2.34 1.23-3.17-.12-.3-.53-1.52.12-3.16 0 0 1-.32 3.3 1.21a11.5 11.5 0 0 1 6 0c2.3-1.53 3.29-1.21 3.29-1.21.65 1.64.24 2.86.12 3.16.77.83 1.23 1.88 1.23 3.17 0 4.53-2.81 5.53-5.49 5.82.43.37.81 1.1.81 2.22 0 1.6-.01 2.9-.01 3.29 0 .31.21.68.83.56A12.3 12.3 0 0 0 24 12.29C24 5.78 18.63.5 12 .5z" />
  </svg>
);
import {
  Atlas, AtlasNode, loadAtlas, glyphFor, REL_ORDER, OVERVIEW_RELS,
  humanizeToken,
} from './atlas';

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

function NavRow({ atlas, id, active, depth, expandable, expanded, onToggle, onOpen, count }: {
  atlas: Atlas; id: string; active: boolean; depth: number; expandable: boolean;
  expanded: boolean; onToggle: () => void; onOpen: () => void; count?: number;
}) {
  const n = atlas.nodes[id];
  if (!n) return null;
  const Glyph = glyphFor(atlas.typeMeta[n.type]?.glyph || 'BookOpen');
  return (
    <div className="nav-row" data-active={active} role="button" tabIndex={0}
      aria-label={n.title} aria-current={active ? 'true' : undefined}
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
      {count != null && <span className="nav-row__count">{count}</span>}
    </div>
  );
}

function Sidebar({ atlas, selectedId, onOpen, onHome, search, onSearch, results, expanded, toggle }: {
  atlas: Atlas; selectedId: string | null; onOpen: (id: string) => void; onHome: () => void;
  search: string; onSearch: (e: any) => void; results: any[];
  expanded: Set<string>; toggle: (key: string) => void;
}) {
  const is = (k: string) => expanded.has(k);

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
            <div className="nav__section-label"><Compass /> Adversary objectives</div>
            {atlas.nav.objectives.map(obj => {
              const gKey = `g:${obj.goalId}`;
              const gOpen = is(gKey);
              return (
                <div key={obj.goalId}>
                  <NavRow atlas={atlas} id={obj.goalId} active={selectedId === obj.goalId} depth={0}
                    expandable={obj.families.length + obj.looseAttackIds.length > 0} expanded={gOpen}
                    onToggle={() => toggle(gKey)} onOpen={() => onOpen(obj.goalId)} count={obj.count} />
                  {gOpen && (
                    <div className="nav-children">
                      {obj.families.map(fam => {
                        const fKey = `${gKey}/f:${fam.id}`;
                        const fOpen = is(fKey);
                        return (
                          <div key={fam.id}>
                            <NavRow atlas={atlas} id={fam.id} active={selectedId === fam.id} depth={1}
                              expandable={fam.attackIds.length > 0} expanded={fOpen}
                              onToggle={() => toggle(fKey)} onOpen={() => onOpen(fam.id)} count={fam.attackIds.length} />
                            {fOpen && fam.attackIds.map(aid => (
                              <NavRow key={aid} atlas={atlas} id={aid} active={selectedId === aid} depth={2}
                                expandable={false} expanded={false} onToggle={() => {}} onOpen={() => onOpen(aid)} />
                            ))}
                          </div>
                        );
                      })}
                      {obj.looseAttackIds.map(aid => (
                        <NavRow key={aid} atlas={atlas} id={aid} active={selectedId === aid} depth={1}
                          expandable={false} expanded={false} onToggle={() => {}} onOpen={() => onOpen(aid)} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {atlas.nav.sections.map(sec => {
              const sKey = `s:${sec.id}`;
              const sOpen = is(sKey);
              const Glyph = glyphFor(sec.glyph);
              const total = sec.groups.reduce((a, g) => a + g.ids.length, 0);
              return (
                <div key={sec.id}>
                  <button className="nav__section-label" style={{ width: '100%' }} onClick={() => toggle(sKey)}>
                    {sOpen ? <ChevronDown /> : <ChevronRight />}<Glyph /> {sec.label}
                    <span style={{ marginLeft: 'auto', opacity: 0.7 }}>{total}</span>
                  </button>
                  {sOpen && sec.groups.map(grp => (
                    <div key={grp.label}>
                      {sec.groups.length > 1 && (
                        <div style={{ padding: '0.4rem 0.75rem 0.15rem 1.6rem', fontFamily: 'var(--mono)', fontSize: '0.6rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--theme-muted)', opacity: 0.8 }}>{grp.label}</div>
                      )}
                      {grp.ids.map(id => (
                        <NavRow key={id} atlas={atlas} id={id} active={selectedId === id} depth={1}
                          expandable={false} expanded={false} onToggle={() => {}} onOpen={() => onOpen(id)} />
                      ))}
                    </div>
                  ))}
                </div>
              );
            })}
          </>
        )}
      </div>
    </>
  );
}

/* ---------------------------------------------------------------- landing */

function Landing({ atlas, onOpen }: { atlas: Atlas; onOpen: (id: string) => void }) {
  const c = atlas.meta.counts;
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
          it. Every claim links to a source; nothing here is a working exploit.
        </p>
        <div className="landing__stats">
          <div className="stat"><b>{c.nodes}</b><small>Topics</small></div>
          <div className="stat"><b>{c.edges}</b><small>Relationships</small></div>
          <div className="stat"><b>{c.sources}</b><small>Sources</small></div>
          <div className="stat"><b>{c.types.attack}</b><small>Attacks</small></div>
          <div className="stat"><b>{c.types.defense}</b><small>Defenses</small></div>
        </div>
      </div>

      <div className="eyb" style={{ marginBottom: '1rem' }}><Crosshair style={{ width: '0.85rem', height: '0.85rem' }} /> ADVERSARY OBJECTIVES</div>
      <div className="obj-grid">
        {atlas.nav.objectives.map((obj, i) => {
          const g = atlas.nodes[obj.goalId];
          if (!g) return null;
          const misuse = obj.goalId === 'goal-misuse';
          return (
            <button key={obj.goalId} className={`obj-card ${misuse ? 'obj-card--misuse' : ''}`}
              style={accentVar(atlas, 'goal')} onClick={() => onOpen(obj.goalId)}>
              <div className="obj-card__n">{misuse ? 'ADJACENT LENS' : `OBJECTIVE ${String(i + 1).padStart(2, '0')}`}</div>
              <div className="obj-card__title">{g.title}</div>
              <div className="obj-card__sum">{g.summary}</div>
              <div className="obj-card__foot">
                <span className="obj-card__count"><b>{obj.count}</b> techniques · {obj.families.length} families</span>
                <span className="obj-card__go"><ArrowUpRight style={{ width: '1.1rem', height: '1.1rem' }} /></span>
              </div>
            </button>
          );
        })}
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
      const m = (a.getAttribute('href') || '').match(/^\/nodes\/([^/]+)\/?$/);
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

function Reader({ atlas, node, tab, setTab, onOpen, onGraph }: {
  atlas: Atlas; node: AtlasNode; tab: string; setTab: (t: any) => void;
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

  const isGoal = node.type === 'goal';

  return (
    <div className="reader" style={accentVar(atlas, node.type)}>
      <div className="reader__eyebrow">
        <span className="eyb eyb--accent"><span className="type-dot" /> {meta?.label || node.type}</span>
        {node.evidence_status && <span className="badge badge--ev"><ScrollText />{humanizeToken(node.evidence_status)}</span>}
        {node.content_status && <span className="badge">{node.content_status}</span>}
        {node.priority && <span className="badge">{node.priority}</span>}
      </div>

      <h1>{node.title}</h1>

      {node.aliases?.length > 0 && (
        <div className="aliases">{node.aliases.map(a => <span key={a} className="alias">{a}</span>)}</div>
      )}

      {node.caveat && (
        <div className="caveat"><AlertTriangle /><p>{node.caveat}</p></div>
      )}

      {node.summary && <p className="summary">{node.summary}</p>}

      <div className="tabs">
        <button className="tab" data-on={tab === 'overview'} onClick={() => setTab('overview')}>Overview</button>
        <button className="tab" data-on={tab === 'evidence'} onClick={() => setTab('evidence')}>Evidence<span className="tab__n">{evCount}</span></button>
        <button className="tab" data-on={tab === 'map'} onClick={() => setTab('map')}>Relationships<span className="tab__n">{relCount}</span></button>
      </div>

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
          <a className="readmore" href={`/nodes/${node.id}/`} target="_blank" rel="noreferrer">
            <BookOpen /> Open full article
          </a>
          <button className="readmore desktop-only" style={{ marginLeft: '0.6rem', background: 'transparent', color: 'var(--theme-ink)' }} onClick={onGraph}>
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
  );
}

/* ------------------------------------------------------------------ graph */

function GraphView({ atlas, focusId, onOpen, fullWidth }: {
  atlas: Atlas; focusId: string | null; onOpen: (id: string) => void; fullWidth: boolean;
}) {
  const ref = useRef<any>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 400, h: 400 });
  const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setDims({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setDims({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  // Local neighborhood projection (PRD 7.5): focus + direct relations, capped.
  const data = useMemo(() => {
    const ids = new Set<string>();
    if (focusId && atlas.nodes[focusId]) {
      ids.add(focusId);
      const rel = atlas.nodes[focusId].rel || {};
      Object.values(rel).flat().forEach(id => ids.add(id));
    } else {
      // Overview: goals + their families.
      atlas.nav.objectives.forEach(o => {
        ids.add(o.goalId);
        o.families.forEach(f => ids.add(f.id));
      });
    }
    const capped = Array.from(ids).slice(0, 150);
    const idSet = new Set(capped);
    const nodes = capped.map(id => {
      const n = atlas.nodes[id];
      const focus = id === focusId;
      // Pin the focus node at the origin so the neighborhood forms a clean hub.
      return { id, name: n.title, type: n.type, color: atlas.typeMeta[n.type]?.color, focus,
        ...(focus ? { fx: 0, fy: 0 } : {}) };
    });
    const links = atlas.edges
      .filter(e => idSet.has(e.source) && idSet.has(e.target))
      .map(e => ({ source: e.source, target: e.target, type: e.type }));
    return { nodes, links };
  }, [atlas, focusId]);

  // Spread the neighborhood so labels don't collide; pin fit after settle.
  useEffect(() => {
    const g = ref.current;
    if (!g) return;
    try {
      g.d3Force('charge')?.strength(-220);
      g.d3Force('link')?.distance(70);
    } catch {}
    const t = setTimeout(() => g.zoomToFit(400, 85), reduced ? 60 : 650);
    return () => clearTimeout(t);
  }, [data, reduced]);

  const drawNode = useCallback((node: any, ctx: CanvasRenderingContext2D, scale: number) => {
    const ink = getComputedStyle(document.documentElement).getPropertyValue('--theme-ink').trim() || '#111';
    const surface = getComputedStyle(document.documentElement).getPropertyValue('--theme-bg').trim() || '#fff';
    const r = node.focus ? 6.5 : 4.5;
    // node disc
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = node.color || '#888';
    ctx.fill();
    if (node.focus) {
      ctx.lineWidth = 2.4 / scale;
      ctx.strokeStyle = ink;
      ctx.stroke();
    }
    // label below the node with a legibility backing plate
    if (scale > 0.45 || node.focus) {
      const label = node.name.length > 26 ? node.name.slice(0, 24) + '…' : node.name;
      const fs = node.focus ? 5.2 : 4.4;
      ctx.font = `${node.focus ? 600 : 450} ${fs}px ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const tw = ctx.measureText(label).width;
      const pad = 1.4;
      const ly = node.y + r + 2.2;
      ctx.globalAlpha = 0.82;
      ctx.fillStyle = surface;
      ctx.fillRect(node.x - tw / 2 - pad, ly - pad, tw + pad * 2, fs + pad * 2);
      ctx.globalAlpha = 1;
      ctx.fillStyle = ink;
      ctx.fillText(label, node.x, ly);
    }
  }, []);

  const legendTypes = useMemo(() => {
    const present = new Set(data.nodes.map(n => n.type));
    return Object.entries(atlas.typeMeta)
      .filter(([t]) => present.has(t))
      .sort((a, b) => a[1].order - b[1].order);
  }, [data, atlas]);

  return (
    <div className="graphwrap" ref={wrapRef}>
      <ForceGraph2D
        ref={ref}
        width={dims.w}
        height={dims.h}
        graphData={data}
        nodeCanvasObject={drawNode}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
          ctx.fill();
        }}
        onNodeClick={(node: any) => onOpen(node.id)}
        linkColor={() => getComputedStyle(document.documentElement).getPropertyValue('--hair-strong') || '#ccc'}
        linkWidth={1}
        linkDirectionalArrowLength={2.5}
        linkDirectionalArrowRelPos={1}
        cooldownTicks={reduced ? 0 : 80}
        d3VelocityDecay={0.35}
        backgroundColor="transparent"
      />
      <div className="graph-hint">{focusId ? atlas.nodes[focusId]?.title : 'Adversary objectives'} · local map</div>
      <div className="graph-tools">
        <button onClick={() => ref.current?.zoomToFit(400, 60)} title="Fit"><Maximize2 /></button>
      </div>
      <div className="graph-legend">
        {legendTypes.map(([t, m]) => (
          <span key={t}><i style={{ background: m.color }} />{m.label}</span>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------- app */

export function GraphApp() {
  const [atlas, setAtlas] = useState<Atlas | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [trail, setTrail] = useState<string[]>([]);
  const [tab, setTab] = useState<'overview' | 'evidence' | 'map'>('overview');
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphFull, setGraphFull] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
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
      for (const obj of a.nav.objectives) {
        if (obj.goalId === id) next.add(`g:${id}`);
        for (const fam of obj.families) {
          if (fam.id === id) next.add(`g:${obj.goalId}`);
          if (fam.attackIds.includes(id)) { next.add(`g:${obj.goalId}`); next.add(`g:${obj.goalId}/f:${fam.id}`); }
        }
        if (obj.looseAttackIds.includes(id)) next.add(`g:${obj.goalId}`);
      }
      for (const sec of a.nav.sections) {
        if (sec.groups.some(g => g.ids.includes(id))) next.add(`s:${sec.id}`);
      }
      return next;
    });
  }, []);

  const open = useCallback((id: string, opts: { push?: boolean } = {}) => {
    if (!atlas || !atlas.nodes[id]) return;
    setSelectedId(id);
    setTab('overview');
    setTrail(prev => opts.push ? [...prev.filter(x => x !== id), id] : [id]);
    expandAncestors(id, atlas);
    setMobileTab('home');
    setSearch(''); setResults([]);
    try { history.pushState({ id }, '', `/?node=${id}`); } catch {}
    document.querySelector('.stage__reader')?.scrollTo({ top: 0 });
  }, [atlas, expandAncestors]);

  // Chip / in-reader navigation pushes to the trail.
  const openLink = useCallback((id: string) => open(id, { push: true }), [open]);

  // --- URL restore + back/forward ---
  useEffect(() => {
    if (!atlas) return;
    const applyFromURL = () => {
      const p = new URLSearchParams(window.location.search);
      const id = p.get('node');
      if (id && atlas.nodes[id]) { setSelectedId(id); setTrail([id]); expandAncestors(id, atlas); setMobileTab('home'); }
      else { setSelectedId(null); setMobileTab('home'); }
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

  const goHome = useCallback(() => {
    setSelectedId(null); setTrail([]); setGraphFull(false); setMobileTab('home');
    setSearch(''); setResults([]);
    try { history.pushState({}, '', '/'); } catch {}
  }, []);

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
          results={results} expanded={expanded} toggle={toggleKey} />
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
          <div className="stage"><div className="stage__graph"><GraphView atlas={atlas} focusId={selectedId} onOpen={open} fullWidth /></div></div>
        ) : (
          <div className={`stage ${graphFull ? 'stage--graphonly' : ''}`}>
            <div className="stage__reader">
              {node
                ? <Reader atlas={atlas} node={node} tab={tab} setTab={setTab} onOpen={openLink} onGraph={() => { setGraphOpen(true); }} />
                : <Landing atlas={atlas} onOpen={open} />}
            </div>
            {showGraph && (
              <div className="stage__graph desktop-only">
                <GraphView atlas={atlas} focusId={selectedId} onOpen={openLink} fullWidth={graphFull} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* MOBILE TAB BAR */}
      <nav className="mtabbar">
        <button className="mtab" data-on={mobileTab === 'home' && !selectedId} onClick={goHome}><Home /> Home</button>
        <button className="mtab" data-on={mobileTab === 'index'} onClick={() => setMobileTab('index')}><ListIcon /> Index</button>
        <button className="mtab" data-on={mobileTab === 'graph'} onClick={() => setMobileTab('graph')}><Share2 /> Graph</button>
      </nav>
    </div>
  );
}

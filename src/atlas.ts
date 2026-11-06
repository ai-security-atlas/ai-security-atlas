// Shared data layer for the AI Security Atlas explorer.
// Loads the denormalized atlas produced by json2hugo.py and exposes typed
// helpers so views never re-scan the raw edge list.

import {
  Target, Layers, Crosshair, FlaskConical, ShieldCheck, Gauge, Lightbulb,
  Cpu, Boxes, GitBranch, Binary, BookOpen,
} from 'lucide-react';

export interface Observation {
  id?: string; target_label?: string; claim?: string; limitations?: string;
  source_id?: string; verification_depth?: string; reproduced?: boolean;
}
export interface Framework {
  framework: string; edition?: string; external_id: string; title: string; source_id?: string;
}
export interface AtlasNode {
  id: string; title: string; type: string; summary: string;
  aliases: string[]; caveat: string; priority: string;
  content_status: string; evidence_status: string; last_reviewed: string;
  references: string[]; access_profile_ids: string[];
  observations: Observation[]; frameworks: Framework[];
  rel: Record<string, string[]>;
  has_article?: boolean;
  lab?: Lab;
  practiced_in?: PracticedIn;    // covered by another lab's steps (lab front matter `covers:`)
  labs_in_area?: AreaLab[];      // hub nodes only: existing labs that practice its members
  primary_goal?: string;         // attacks only: the goal whose nav row is canonical; other goals show an alias
  planned_lab?: PlannedLab;      // roadmap: an own lab is planned for this node (no lab folder yet)
  planned_practiced_in?: PlannedPracticedIn;  // roadmap: a planned lab will cover this node
  labs_planned_in_area?: PlannedAreaLab[];    // hub nodes only: planned labs for its members or placed here
}
// A planned (roadmap-only) lab; no page exists yet.
export interface PlannedLab {
  node: string; title: string;
  effort: string;          // roadmap effort, e.g. "S" | "M" | "L" (may be "")
  model_backend: string;   // "none" | "optional" | "required" | ""
  status: 'planned';
  objectives: string[]; families: string[];  // derived like Lab.objectives / Lab.families
  covers: string[];        // roadmap also_covers node ids
}
export interface PlannedPracticedIn {
  node: string; title: string; status: 'planned';
  where: string;           // roadmap note on where the planned lab practices this node
}
export interface PlannedAreaLab {
  node: string; title: string; effort: string; status: 'planned';
  relation: 'own' | 'practiced' | 'foundation';
}
// A covered node points at the lab steps that practice it.
export interface PracticedIn {
  lab_id: string; number: number; node: string; title: string;
  steps: string;  // e.g. "4-7, D1"
  url: string;    // lab page (/labs/<lab>/) at the first step's guide anchor
}
// One row of a hub's "Labs in this area" list.
export interface AreaLab {
  lab_id: string; number: number; node: string; title: string;
  level: string; time: string;
  page: string;   // lab page (/labs/<id>/)
  own: boolean;   // the lab's own node is a member of the hub
  practiced: { node: string; steps: string; url: string }[];  // url: /labs/<id>/#<anchor>
  relation: 'own' | 'practiced' | 'foundation';  // own node is a member > covers a member > placed by derivation
  family: string; // family the row groups under (the hub itself on a family hub)
}
// Hands-on lab metadata, compiled from labs/<node-id>/README.md front matter.
export interface Lab {
  lab_id: string; number: number; node: string; title: string;
  family: string;     // graph-derived family (families[0]); front matter value only when nothing is derived
  level: string; time: string; model_backend: string; backends: Record<string, string>;
  last_tested: string;
  github: string;     // GitHub URL of the lab folder
  page: string;       // site path of the lab page (/labs/<id>/): explainer on top, then the guide (#lab-guide)
  explainer: string;  // the lab page when the lab has an explainer, or "" if none
  covers?: { node: string; steps: string; anchor: string }[];
  objectives: string[];  // goals this lab sits under (attack lab: its goals, primary first); [] = foundations only
  families: string[];    // technique families this lab sits under (0-2)
}
export interface Source {
  id: string; title: string; url: string; kind: string; publisher: string;
  year: number | string; verification_depth: string; relevance: string;
  full_text_reviewed: boolean; experiments_reproduced: boolean; node_ids: string[];
}
export interface AccessProfile {
  id: string; title: string; all_of: string[]; any_of: string[];
  not_required: string[]; caveat: string;
}
export interface AtlasView {
  id: string; title: string; description: string; root_ids: string[];
  node_types: string[]; edge_types: string[]; learning_path: string[];
  max_initial_nodes: number; max_visible_nodes: number; show_sources: boolean;
}
export interface TypeMeta {
  label: string; plural: string; glyph: string; color: string; order: number;
}
export interface Objective {
  goalId: string;
  families: {
    id: string; attackIds: string[];
    attacks: { id: string; primary: boolean }[];  // primary=false: alias row (this goal is not its primary_goal)
    primaryCount: number;
  }[];
  looseAttackIds: string[];
  count: number;
  primaryCount: number;  // attacks whose primary_goal is this goal
}
// Derived goal <- family edge (not authored): family attacks that serve the goal.
export interface FamilyGoal {
  goal: string; family: string; attack_count: number; primary_count: number;
}
export interface NavSection {
  id: string; label: string; glyph: string;
  groups: { label: string; ids: string[] }[];
}
export interface Atlas {
  meta: {
    title: string; as_of: string; status: string; schema_version: string;
    research_disclosure: string;
    counts: { nodes: number; edges: number; sources: number; views: number; labs?: number; labs_planned?: number; types: Record<string, number> };
  };
  typeMeta: Record<string, TypeMeta>;
  relLabels: Record<string, string>;
  nodes: Record<string, AtlasNode>;
  edges: { source: string; target: string; type: string; conditions: string }[];
  sources: Record<string, Source>;
  accessProfiles: Record<string, AccessProfile>;
  views: AtlasView[];
  nav: { objectives: Objective[]; sections: NavSection[] };
  familyGoals: FamilyGoal[];  // in nav order (GOAL_ORDER, then family title)
  labs?: Lab[];  // ordered by lab number
}

// Icon registry maps the glyph names emitted by the compiler to components.
export const GLYPHS: Record<string, any> = {
  Target, Layers, Crosshair, FlaskConical, ShieldCheck, Gauge, Lightbulb,
  Cpu, Boxes, GitBranch, Binary, BookOpen,
};

export function glyphFor(name: string) {
  return GLYPHS[name] || BookOpen;
}

// Ordered relationship groups shown in the reader, with the direction each
// heading implies. Only non-empty groups render.
export const REL_ORDER: string[] = [
  'routesToGoal', 'reachableVia', 'memberOf', 'hasMember',
  'requires', 'requiredBy', 'mitigatedBy', 'canMitigate',
  'evaluatedBy', 'evaluates', 'inScopeOf', 'hasRelevantTopic',
  'uses', 'usedBy', 'variantOf', 'hasVariant',
  'canEnable', 'mayBeEnabledBy', 'distinctFrom',
];

// Which relationship groups belong to the "Overview" tab (the essentials) vs
// the exhaustive "Relationships" tab. Keyed loosely; everything shows in Map.
export const OVERVIEW_RELS: Record<string, string[]> = {
  goal: ['reachableVia'],
  technique_family: ['hasMember', 'routesToGoal'],
  attack: ['routesToGoal', 'memberOf', 'requires', 'mitigatedBy', 'evaluatedBy', 'inScopeOf', 'variantOf', 'canEnable'],
  defense: ['canMitigate', 'requires', 'inScopeOf'],
  method: ['usedBy', 'requires', 'inScopeOf', 'variantOf'],
  evaluation: ['evaluates', 'requires'],
  concept: ['requiredBy', 'requires', 'hasRelevantTopic'],
  architecture: ['hasRelevantTopic', 'requiredBy', 'requires'],
  component: ['hasRelevantTopic', 'requiredBy'],
  lifecycle: ['requiredBy', 'hasRelevantTopic'],
  format: ['hasRelevantTopic', 'requiredBy', 'requires'],
};

export async function loadAtlas(): Promise<Atlas> {
  // no-cache => conditional revalidation, so a redeploy's atlas is never stale.
  const res = await fetch('/data/atlas.json', { cache: 'no-cache' });
  if (!res.ok) throw new Error(`atlas fetch failed: ${res.status}`);
  return res.json();
}

// Human-readable capability tokens used inside access profiles.
export function humanizeToken(t: string): string {
  return t.replace(/_/g, ' ');
}

export function titleOf(atlas: Atlas, id: string): string {
  return atlas.nodes[id]?.title || atlas.sources[id]?.title || id;
}

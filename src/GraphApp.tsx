import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Search, ShieldAlert, Cpu, Network, Shield, ChevronRight, ChevronDown, Maximize2, BookOpen, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const IndexTreeNode = ({ node, parentId, path, getChildren, expandedIndexNodes, toggleIndexNode, handleNodeClick, selectedNode, getIconForType, depth = 0 }) => {
  const children = getChildren(node.id, parentId);
  const currentPath = path ? `${path}/${node.id}` : node.id;
  const isExpanded = expandedIndexNodes.has(currentPath);
  const isSelected = selectedNode?.id === node.id;
  
  return (
    <div className="mb-0.5">
      <div 
        className={`flex items-center gap-2 py-1.5 cursor-pointer transition-colors ${
          isSelected ? 'bg-[color-mix(in_srgb,currentColor_5%,transparent)] text-[var(--theme-ink)] font-medium' : 'text-[var(--theme-muted)] hover:text-[var(--theme-ink)] hover:bg-[color-mix(in_srgb,currentColor_3%,transparent)]'
        }`}
        style={{ paddingLeft: `${depth * 1.25 + 0.75}rem`, paddingRight: '0.75rem' }}
        onClick={() => handleNodeClick(node)}
      >
        <button 
          onClick={(e) => toggleIndexNode(e, currentPath)}
          className={`p-0.5 rounded text-[var(--theme-muted)] hover:text-[var(--theme-ink)] ${children.length === 0 ? 'invisible' : ''}`}
        >
          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
        <div className="shrink-0">{getIconForType(node.type, "w-3.5 h-3.5")}</div>
        <span className="text-sm truncate select-none">{node.name}</span>
      </div>
      
      <AnimatePresence>
        {isExpanded && children.length > 0 && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            {children.map(child => (
              <IndexTreeNode 
                key={`${currentPath}/${child.id}`}
                node={child}
                parentId={node.id}
                path={currentPath}
                getChildren={getChildren}
                expandedIndexNodes={expandedIndexNodes}
                toggleIndexNode={toggleIndexNode}
                handleNodeClick={handleNodeClick}
                selectedNode={selectedNode}
                getIconForType={getIconForType}
                depth={depth + 1}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export function GraphApp() {
  const [data, setData] = useState({ nodes: [], links: [], allEdges: [] });
  const [visibleNodeIds, setVisibleNodeIds] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [expandedIndexNodes, setExpandedIndexNodes] = useState(new Set());

  useEffect(() => {
    const initPagefind = async () => {
      if (typeof window !== 'undefined' && !window.pagefind) {
        try {
          window.pagefind = await import(/* @vite-ignore */ '/pagefind/pagefind.js');
          await window.pagefind.options({ baseUrl: '/' });
          await window.pagefind.init();
        } catch (e) {
          console.error('Failed to load pagefind', e);
        }
      }
    };
    initPagefind();
  }, []);

  const handleSearchChange = async (e) => {
    const query = e.target.value;
    setSearch(query);
    if (!query) {
      setSearchResults([]);
      return;
    }
    if (window.pagefind) {
      const searchData = await window.pagefind.search(query);
      const results = await Promise.all(searchData.results.map(r => r.data()));
      setSearchResults(results);
    } else {
      setSearchResults(
        data.nodes
          .filter(n => n.name.toLowerCase().includes(query.toLowerCase()))
          .map(n => ({
            url: `/nodes/${n.id}/`,
            meta: { title: n.name },
            excerpt: n.summary || ''
          }))
      );
    }
  };

  const onResultClick = (result) => {
    const match = result.url.match(/\/(?:nodes|sources)\/([^/]+)/);
    if (match) {
      const id = match[1];
      const node = data.nodes.find(n => n.id === id) || (data.sources && data.sources.find(s => s.id === id));
      if (node) {
        handleNodeClick(node);
      } else {
        window.location.href = result.url;
      }
    } else {
      window.location.href = result.url;
    }
  };

  
  // Mobile UI and Graph Toggle state
  const [isMobileIndexOpen, setIsMobileIndexOpen] = useState(true);
  const [showGraph, setShowGraph] = useState(false);
  
  const graphRef = useRef();

  // Color mapping based on 0perant theme feel
  const getColor = (type) => {
    switch(type) {
      case 'goal': return 'var(--theme-action)'; 
      case 'attack': return '#e11d48'; 
      case 'architecture': return '#2563eb';
      case 'concept': return '#059669';
      case 'method': return '#7c3aed';
      default: return 'var(--theme-muted)';
    }
  };

  useEffect(() => {
    fetch('/data/graph.json')
      .then(res => res.json())
      .then(json => {
        const nodes = json.nodes.map(n => ({
          ...n,
          id: n.id,
          name: n.title,
          val: n.type === 'goal' ? 4 : n.type === 'attack' ? 3 : 2
        }));
        
        const allEdges = json.edges || [];
        
        const links = allEdges.map(e => ({
          source: e.source,
          target: e.target,
          type: e.type,
          name: e.conditions
        })).filter(l => 
          nodes.some(n => n.id === l.source) && 
          nodes.some(n => n.id === l.target)
        );

        setData({ nodes, links, allEdges });
        
        // Initial visible nodes: only goals
        const initialVisible = new Set(nodes.filter(n => n.type === 'goal').map(n => n.id));
        setVisibleNodeIds(initialVisible);
      });
  }, []);

  const expandNode = useCallback((nodeId) => {
    setVisibleNodeIds(prev => {
      const next = new Set(prev);
      next.add(nodeId);
      // Add all directly connected nodes
      data.links.forEach(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        if (sourceId === nodeId) next.add(targetId);
        if (targetId === nodeId) next.add(sourceId);
      });
      return next;
    });
  }, [data.links]);

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
    expandNode(node.id);
    setExpandedIndexNodes(prev => {
      const next = new Set(prev);
      next.add(node.id);
      return next;
    });
    
    // Switch to content view on mobile
    setIsMobileIndexOpen(false);
    
    if (showGraph && graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(1.5, 1000);
    }
  }, [expandNode, showGraph]);

  const getIconForType = (type, className = "w-4 h-4") => {
    switch(type) {
      case 'goal': return <ShieldAlert className={className} style={{ color: getColor(type) }} />;
      case 'architecture': return <Cpu className={className} style={{ color: getColor(type) }} />;
      case 'method': return <Network className={className} style={{ color: getColor(type) }} />;
      case 'attack': return <Shield className={className} style={{ color: getColor(type) }} />;
      default: return <BookOpen className={className} style={{ color: getColor(type) }} />;
    }
  };

  const graphData = useMemo(() => {
    const visibleNodes = data.nodes.filter(n => visibleNodeIds.has(n.id));
    const visibleLinks = data.links.filter(l => {
      const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
      const targetId = typeof l.target === 'object' ? l.target.id : l.target;
      return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
    });
    return { nodes: visibleNodes, links: visibleLinks };
  }, [data, visibleNodeIds]);

  // Helper to find children recursively
  const getChildren = useCallback((nodeId, parentId) => {
    const adjacentIds = new Set();
    data.links.forEach(l => {
      const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
      const targetId = typeof l.target === 'object' ? l.target.id : l.target;
      if (sourceId === nodeId && targetId !== parentId) adjacentIds.add(targetId);
      if (targetId === nodeId && sourceId !== parentId) adjacentIds.add(sourceId);
    });
    return data.nodes.filter(n => adjacentIds.has(n.id));
  }, [data]);

  const toggleIndexNode = (e, nodeId) => {
    e.stopPropagation();
    setExpandedIndexNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  };

  return (
    <div className="flex h-screen w-full bg-[var(--theme-bg)] text-[var(--theme-ink)] font-sans overflow-hidden">
      
      {/* Left Sidebar - Index */}
      <div className={`${isMobileIndexOpen ? 'flex' : 'hidden'} md:flex w-full md:w-[350px] border-r border-[color-mix(in_srgb,currentColor_15%,transparent)] bg-[var(--theme-surface)] flex-col z-10 shrink-0 shadow-[4px_0_24px_rgba(0,0,0,0.02)]`}>
        <div className="p-5 border-b border-[color-mix(in_srgb,currentColor_15%,transparent)]">
          <h2 className="mb-4 flex items-center gap-2 font-bold" style={{ fontSize: '1.25rem' }}>
            <Shield className="w-5 h-5 text-[var(--theme-action)]" /> AI Security Atlas
          </h2>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--theme-muted)]" />
            <input 
              type="text"
              placeholder="Search concepts..."
              className="w-full pl-9 pr-4 py-2 bg-[var(--theme-bg)] border border-[color-mix(in_srgb,currentColor_25%,transparent)] rounded-none focus:outline-none focus:border-[var(--theme-focus)] text-sm transition-colors"
              value={search}
              onChange={handleSearchChange}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {search ? (
            <div className="space-y-1">
              {searchResults.map((result, idx) => (
                <div 
                  key={idx}
                  className="px-3 py-2 hover:bg-[color-mix(in_srgb,currentColor_5%,transparent)] cursor-pointer flex flex-col gap-1 transition-colors border-b border-[color-mix(in_srgb,currentColor_10%,transparent)] last:border-0"
                  onClick={() => onResultClick(result)}
                >
                  <div className="text-sm font-medium text-[var(--theme-ink)]">{result.meta?.title || result.url}</div>
                  <div 
                    className="text-xs text-[var(--theme-muted)] line-clamp-2 [&>mark]:bg-[var(--theme-focus)] [&>mark]:text-white [&>mark]:px-0.5 [&>mark]:rounded-sm" 
                    dangerouslySetInnerHTML={{ __html: result.excerpt }} 
                  />
                </div>
              ))}
              {searchResults.length === 0 && (
                <div className="p-4 text-sm text-[var(--theme-muted)] text-center">
                  No results found.
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-1 pt-2">
              <div className="px-3 pb-2 text-xs font-semibold tracking-widest uppercase text-[var(--theme-muted)]">
                Index
              </div>
              {data.nodes.filter(n => n.type === 'goal').map(goal => (
                <IndexTreeNode 
                  key={goal.id}
                  node={goal}
                  parentId={null}
                  path={null}
                  getChildren={getChildren}
                  expandedIndexNodes={expandedIndexNodes}
                  toggleIndexNode={toggleIndexNode}
                  handleNodeClick={handleNodeClick}
                  selectedNode={selectedNode}
                  getIconForType={getIconForType}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className={`${!isMobileIndexOpen ? 'flex' : 'hidden'} md:flex flex-1 flex-col relative min-w-0`}>
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[color-mix(in_srgb,currentColor_15%,transparent)] bg-[var(--theme-surface)] shrink-0 h-[73px]">
          <div className="flex items-center gap-4">
            <button 
              className="md:hidden flex items-center gap-2 text-[var(--theme-muted)] hover:text-[var(--theme-ink)]"
              onClick={() => setIsMobileIndexOpen(true)}
            >
              <ChevronRight className="w-5 h-5 rotate-180" />
              <span className="text-sm font-medium">Index</span>
            </button>
            <div className="hidden md:block text-sm font-medium text-[var(--theme-muted)] truncate max-w-md">
              {selectedNode ? selectedNode.name : 'Select a topic'}
            </div>
          </div>
          <button 
            onClick={() => setShowGraph(!showGraph)}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium border transition-colors ${
              showGraph 
                ? 'bg-[var(--theme-action)] text-white border-[var(--theme-action)]' 
                : 'border-[color-mix(in_srgb,currentColor_15%,transparent)] hover:border-[var(--theme-action)]'
            }`}
          >
            <Network className="w-4 h-4" />
            {showGraph ? 'Hide Graph' : 'View Graph'}
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto relative bg-[var(--theme-bg)]">
          {showGraph ? (
            <div className="absolute inset-0 cursor-move">
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeLabel="name"
                nodeColor={node => {
                  if (selectedNode && selectedNode.id === node.id) return 'var(--theme-focus)';
                  if (hoverNode && hoverNode.id === node.id) return 'var(--theme-action)';
                  return getColor(node.type);
                }}
                nodeRelSize={5}
                linkColor={() => 'color-mix(in srgb, currentColor 15%, transparent)'}
                linkWidth={1.5}
                onNodeClick={handleNodeClick}
                onNodeHover={setHoverNode}
                d3VelocityDecay={0.3}
                backgroundColor="var(--theme-bg)"
              />
              <div className="absolute top-4 right-4 z-10">
                <button 
                  onClick={() => {
                    if (graphRef.current) graphRef.current.zoomToFit(400);
                  }}
                  className="p-2 bg-[var(--theme-surface)] border border-[color-mix(in_srgb,currentColor_15%,transparent)] shadow-sm text-[var(--theme-ink)] hover:text-[var(--theme-action)] transition-colors"
                  title="Zoom to Fit"
                >
                  <Maximize2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ) : selectedNode ? (
            <div className="p-6 md:p-12 max-w-4xl mx-auto w-full">
              <div className="flex items-center gap-2 mb-4">
                {getIconForType(selectedNode.type)}
                <span className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-[var(--theme-muted)]">
                  {selectedNode.type}
                </span>
              </div>
              
              <h1 className="text-3xl md:text-4xl font-bold mb-6 text-[var(--theme-ink)]">
                {selectedNode.name}
              </h1>
              
              {selectedNode.aliases && selectedNode.aliases.length > 0 && (
                <div className="mb-8 flex flex-wrap gap-2">
                  {selectedNode.aliases.map(a => (
                    <span key={a} className="px-3 py-1.5 text-sm bg-[color-mix(in_srgb,currentColor_5%,transparent)] text-[var(--theme-muted)] border border-[color-mix(in_srgb,currentColor_10%,transparent)]">
                      {a}
                    </span>
                  ))}
                </div>
              )}

              {selectedNode.caveat && (
                <div className="mb-8 p-4 bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500 rounded-r">
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-500 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-yellow-800 dark:text-yellow-500 uppercase tracking-wider mb-1">Caveat</h4>
                      <p className="text-yellow-700 dark:text-yellow-400 text-sm leading-relaxed">{selectedNode.caveat}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="prose prose-lg max-w-none text-[var(--theme-muted)] leading-relaxed mb-8">
                <p>{selectedNode.summary || 'No detailed summary available in seed data.'}</p>
              </div>
              
              {selectedNode.scope_ids && selectedNode.scope_ids.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Relevant Scopes</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedNode.scope_ids.map(s => {
                       const scopeNode = data.nodes.find(n => n.id === s);
                       return (
                         <span key={s} className="px-3 py-1.5 text-sm bg-[color-mix(in_srgb,currentColor_5%,transparent)] text-[var(--theme-muted)] border border-[color-mix(in_srgb,currentColor_10%,transparent)] flex items-center gap-2 cursor-pointer hover:bg-[color-mix(in_srgb,currentColor_10%,transparent)]" onClick={() => scopeNode && handleNodeClick(scopeNode)}>
                           <Cpu className="w-3.5 h-3.5" />
                           {scopeNode ? scopeNode.name : s}
                         </span>
                       );
                    })}
                  </div>
                </div>
              )}

              {selectedNode.access_profile_ids && selectedNode.access_profile_ids.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Access Profiles</h3>
                  <div className="grid gap-3">
                    {selectedNode.access_profile_ids.map(apId => {
                      const profile = data.access_profiles.find(ap => ap.id === apId);
                      if (!profile) return null;
                      return (
                        <div key={apId} className="p-4 bg-[color-mix(in_srgb,currentColor_2%,transparent)] border border-[color-mix(in_srgb,currentColor_10%,transparent)] rounded">
                          <h4 className="font-semibold text-[var(--theme-ink)] text-sm mb-1">{profile.title}</h4>
                          {profile.caveat && <p className="text-xs text-[var(--theme-muted)] mt-2 italic">{profile.caveat}</p>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {data.framework_mappings.some(fm => fm.node_ids && fm.node_ids.includes(selectedNode.id)) && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Framework Mappings</h3>
                  <div className="grid gap-3">
                    {data.framework_mappings.filter(fm => fm.node_ids && fm.node_ids.includes(selectedNode.id)).map((fm, idx) => (
                      <div key={idx} className="p-3 flex items-start gap-3 bg-[color-mix(in_srgb,currentColor_2%,transparent)] border border-[color-mix(in_srgb,currentColor_10%,transparent)] rounded">
                        <Database className="w-4 h-4 mt-0.5 text-[var(--theme-muted)] shrink-0" />
                        <div>
                          <div className="text-sm font-medium text-[var(--theme-ink)]">{fm.framework} {fm.edition && `(${fm.edition})`}</div>
                          <div className="text-xs text-[var(--theme-muted)] mt-1">{fm.external_id}: {fm.title}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedNode.claims && selectedNode.claims.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Claims</h3>
                  <div className="space-y-3">
                    {selectedNode.claims.map(claim => (
                      <div key={claim.id} className="p-4 bg-[color-mix(in_srgb,currentColor_2%,transparent)] border border-[color-mix(in_srgb,currentColor_10%,transparent)] rounded">
                        <div className="flex gap-2 items-start mb-2">
                          <FileText className="w-4 h-4 mt-0.5 shrink-0 text-[var(--theme-action)]" />
                          <div className="text-sm text-[var(--theme-ink)] font-medium leading-relaxed">{claim.statement}</div>
                        </div>
                        {claim.limitations && (
                          <div className="text-xs text-[var(--theme-muted)] ml-6 mt-2 border-l-2 pl-3 border-[color-mix(in_srgb,currentColor_15%,transparent)]">
                            <span className="font-semibold">Limitations:</span> {claim.limitations}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedNode.observations && selectedNode.observations.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Observations</h3>
                  <div className="space-y-3">
                    {selectedNode.observations.map(obs => (
                      <div key={obs.id} className="p-4 bg-[color-mix(in_srgb,currentColor_2%,transparent)] border border-[color-mix(in_srgb,currentColor_10%,transparent)] rounded text-sm">
                        <div className="font-semibold text-[var(--theme-ink)] mb-1">Target: {obs.target_label}</div>
                        <div className="text-[var(--theme-muted)] mb-2">{obs.claim}</div>
                        {obs.limitations && (
                          <div className="text-xs text-[var(--theme-muted)] italic border-l-2 pl-3 border-[color-mix(in_srgb,currentColor_15%,transparent)]">
                            {obs.limitations}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedNode.references && selectedNode.references.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Sources</h3>
                  <div className="space-y-2">
                    {selectedNode.references.map(refId => {
                      const source = data.sources.find(s => s.id === refId);
                      return source ? (
                        <a 
                          key={refId} 
                          href={source.url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex items-start gap-3 p-3 bg-[color-mix(in_srgb,currentColor_2%,transparent)] hover:bg-[color-mix(in_srgb,currentColor_5%,transparent)] border border-[color-mix(in_srgb,currentColor_10%,transparent)] rounded transition-colors group"
                        >
                          <LinkIcon className="w-4 h-4 mt-0.5 shrink-0 text-[var(--theme-muted)] group-hover:text-[var(--theme-action)]" />
                          <div>
                            <div className="text-sm font-medium text-[var(--theme-ink)] group-hover:text-[var(--theme-action)] leading-snug">{source.title}</div>
                            <div className="flex gap-3 text-xs text-[var(--theme-muted)] mt-1.5">
                              {source.year && <span>{source.year}</span>}
                              {source.kind && <span className="capitalize">{source.kind.replace(/_/g, ' ')}</span>}
                              {source.verification_depth && <span className="text-[var(--theme-action)]">{source.verification_depth.replace(/_/g, ' ')}</span>}
                            </div>
                          </div>
                        </a>
                      ) : (
                        <div key={refId} className="text-sm text-[var(--theme-muted)]">{refId}</div>
                      );
                    })}
                  </div>
                </div>
              )}

              {selectedNode.prerequisites && selectedNode.prerequisites.length > 0 && (
                <div className="mb-12">
                  <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-4">Prerequisites</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {selectedNode.prerequisites.map(reqId => {
                      const reqNode = data.nodes.find(n => n.id === reqId);
                      return reqNode ? (
                        <button 
                          key={reqId}
                          onClick={() => handleNodeClick(reqNode)}
                          className="flex flex-col p-4 border border-[color-mix(in_srgb,currentColor_15%,transparent)] hover:border-[var(--theme-action)] text-left group transition-colors bg-[var(--theme-surface)]"
                        >
                          <div className="flex items-center gap-2 mb-2 w-full">
                            {getIconForType(reqNode.type, "w-4 h-4 shrink-0")}
                            <span className="text-[0.65rem] font-bold uppercase tracking-[0.1em] text-[var(--theme-muted)]">
                              {reqNode.type}
                            </span>
                          </div>
                          <div className="flex items-center justify-between w-full">
                            <span className="text-base font-medium text-[var(--theme-ink)] line-clamp-1 pr-2">{reqNode.name}</span>
                            <ArrowRight className="w-5 h-5 shrink-0 text-[var(--theme-muted)] group-hover:text-[var(--theme-action)]" />
                          </div>
                        </button>
                      ) : null;
                    })}
                  </div>
                </div>
              )}

              <div className="pt-8 border-t border-[color-mix(in_srgb,currentColor_15%,transparent)]">
                <a 
                  href={`/nodes/${selectedNode.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex min-h-[48px] items-center justify-center gap-2 border border-current px-6 py-2.5 text-base font-[650] leading-none transition-colors w-full sm:w-auto bg-[var(--theme-ink)] text-[var(--theme-bg)] hover:bg-[var(--theme-action)] hover:border-[var(--theme-action)]"
                >
                  <BookOpen className="w-5 h-5" /> View Full Article
                </a>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-[var(--theme-muted)] p-8 text-center">
              <BookOpen className="w-16 h-16 mb-4 opacity-20" />
              <h2 className="text-xl font-medium mb-2 text-[var(--theme-ink)]">Welcome to the Atlas</h2>
              <p className="max-w-md">Select a topic from the index on the left to explore its details, or toggle the graph view to see how concepts are connected.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

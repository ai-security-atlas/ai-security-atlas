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
  const [expandedIndexNodes, setExpandedIndexNodes] = useState(new Set());
  
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
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {search ? (
            <div className="space-y-1">
              {data.nodes.filter(n => n.name.toLowerCase().includes(search.toLowerCase())).map(node => (
                <div 
                  key={node.id}
                  className="px-3 py-2 hover:bg-[color-mix(in_srgb,currentColor_5%,transparent)] cursor-pointer flex items-center gap-3 transition-colors"
                  onClick={() => handleNodeClick(node)}
                >
                  {getIconForType(node.type)}
                  <div>
                    <div className="font-medium text-sm text-[var(--theme-ink)]">{node.name}</div>
                  </div>
                </div>
              ))}
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

              <div className="prose prose-lg max-w-none text-[var(--theme-muted)] leading-relaxed mb-12">
                <p>{selectedNode.summary || 'No detailed summary available in seed data.'}</p>
              </div>

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

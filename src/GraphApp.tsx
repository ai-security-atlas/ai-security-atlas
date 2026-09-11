import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Search, ShieldAlert, Cpu, Network, Shield, ChevronRight, ChevronDown, X, Maximize2, BookOpen, ExternalLink, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function GraphApp() {
  const [data, setData] = useState({ nodes: [], links: [], allEdges: [] });
  const [visibleNodeIds, setVisibleNodeIds] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [search, setSearch] = useState('');
  const [expandedIndexNodes, setExpandedIndexNodes] = useState(new Set());
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
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(1.5, 1000);
    }
  }, [expandNode]);

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

  // Build hierarchical index
  const indexTree = useMemo(() => {
    const goals = data.nodes.filter(n => n.type === 'goal');
    return goals.map(goal => {
      // Find children for this goal
      const childrenIds = data.links
        .filter(l => {
          const tId = typeof l.target === 'object' ? l.target.id : l.target;
          return tId === goal.id;
        })
        .map(l => typeof l.source === 'object' ? l.source.id : l.source);
        
      const children = data.nodes.filter(n => childrenIds.includes(n.id));
      return { ...goal, children };
    });
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
      <div className="w-80 border-r border-[color-mix(in_srgb,currentColor_15%,transparent)] bg-[var(--theme-surface)] flex flex-col z-10 shrink-0 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
        <div className="p-5 border-b border-[color-mix(in_srgb,currentColor_15%,transparent)]">
          <h2 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.25rem' }}>
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
              {indexTree.map(goal => (
                <div key={goal.id} className="mb-1">
                  <div 
                    className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                      selectedNode?.id === goal.id ? 'bg-[color-mix(in_srgb,currentColor_5%,transparent)] font-semibold' : 'hover:bg-[color-mix(in_srgb,currentColor_3%,transparent)]'
                    }`}
                    onClick={() => handleNodeClick(goal)}
                  >
                    <button 
                      onClick={(e) => toggleIndexNode(e, goal.id)}
                      className="p-0.5 hover:bg-[color-mix(in_srgb,currentColor_10%,transparent)] rounded text-[var(--theme-muted)]"
                    >
                      {expandedIndexNodes.has(goal.id) ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </button>
                    {getIconForType(goal.type)}
                    <span className="text-sm truncate">{goal.name}</span>
                  </div>
                  
                  <AnimatePresence>
                    {expandedIndexNodes.has(goal.id) && (
                      <motion.div 
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        {goal.children.map(child => (
                          <div 
                            key={child.id}
                            className={`flex items-center gap-2 pl-10 pr-3 py-1.5 cursor-pointer text-sm transition-colors ${
                              selectedNode?.id === child.id ? 'bg-[color-mix(in_srgb,currentColor_5%,transparent)] text-[var(--theme-ink)] font-medium' : 'text-[var(--theme-muted)] hover:text-[var(--theme-ink)]'
                            }`}
                            onClick={() => handleNodeClick(child)}
                          >
                            {getIconForType(child.type, "w-3 h-3")}
                            <span className="truncate">{child.name}</span>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Graph Area */}
      <div className="flex-1 relative cursor-move">
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

        {/* Action Bar */}
        <div className="absolute top-5 right-5 flex gap-2">
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

      {/* Right Panel - Reading Pane */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div 
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="w-96 bg-[var(--theme-surface)] border-l border-[color-mix(in_srgb,currentColor_15%,transparent)] shadow-[-4px_0_24px_rgba(0,0,0,0.05)] flex flex-col z-20 shrink-0 absolute right-0 top-0 bottom-0"
          >
            <div className="flex items-center justify-between p-4 border-b border-[color-mix(in_srgb,currentColor_15%,transparent)]">
              <div className="flex items-center gap-2">
                {getIconForType(selectedNode.type)}
                <span className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-[var(--theme-muted)]">
                  {selectedNode.type}
                </span>
              </div>
              <button 
                onClick={() => setSelectedNode(null)}
                className="p-1.5 hover:bg-[color-mix(in_srgb,currentColor_10%,transparent)] text-[var(--theme-muted)] hover:text-[var(--theme-ink)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1">
              <h2 className="mb-4">
                {selectedNode.name}
              </h2>
              
              {selectedNode.aliases && selectedNode.aliases.length > 0 && (
                <div className="mb-6 flex flex-wrap gap-1.5">
                  {selectedNode.aliases.map(a => (
                    <span key={a} className="px-2 py-1 text-xs bg-[color-mix(in_srgb,currentColor_5%,transparent)] text-[var(--theme-muted)] border border-[color-mix(in_srgb,currentColor_10%,transparent)]">
                      {a}
                    </span>
                  ))}
                </div>
              )}

              <div className="prose prose-sm max-w-none text-[var(--theme-muted)] leading-relaxed mb-8">
                <p>{selectedNode.summary || 'No detailed summary available in seed data.'}</p>
              </div>

              {selectedNode.prerequisites && selectedNode.prerequisites.length > 0 && (
                <div className="mb-8">
                  <h3 className="text-[0.75rem] font-bold uppercase tracking-[0.12em] text-[var(--theme-ink)] mb-3">Prerequisites</h3>
                  <div className="flex flex-col gap-2">
                    {selectedNode.prerequisites.map(reqId => {
                      const reqNode = data.nodes.find(n => n.id === reqId);
                      return reqNode ? (
                        <button 
                          key={reqId}
                          onClick={() => handleNodeClick(reqNode)}
                          className="flex items-center justify-between p-2.5 border border-[color-mix(in_srgb,currentColor_15%,transparent)] hover:border-[var(--theme-action)] text-left group transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            {getIconForType(reqNode.type)}
                            <span className="text-sm font-medium">{reqNode.name}</span>
                          </div>
                          <ArrowRight className="w-4 h-4 text-[var(--theme-muted)] group-hover:text-[var(--theme-action)]" />
                        </button>
                      ) : null;
                    })}
                  </div>
                </div>
              )}

              <div className="mt-8 pt-6 border-t border-[color-mix(in_srgb,currentColor_15%,transparent)]">
                <a 
                  href={`/nodes/${selectedNode.id}`}
                  target="_blank"
                  className="inline-flex min-h-[44px] items-center justify-center gap-2 border border-current px-4 py-2 text-[0.875rem] font-[650] leading-none transition-colors w-full bg-[var(--theme-ink)] text-[var(--theme-bg)] hover:bg-[var(--theme-action)] hover:border-[var(--theme-action)]"
                >
                  <BookOpen className="w-4 h-4" /> View Full Article
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

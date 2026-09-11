import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Search, ShieldAlert, Cpu, Network, Shield, ChevronRight, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export function GraphApp() {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [search, setSearch] = useState('');
  const graphRef = useRef();

  useEffect(() => {
    fetch('/data/graph.json')
      .then(res => res.json())
      .then(json => {
        // Build nodes
        const nodes = json.nodes.map(n => ({
          ...n,
          id: n.id,
          name: n.title,
          val: n.type === 'goal' ? 2 : n.type === 'attack' ? 1.5 : 1
        }));
        
        // Build links from edges
        const links = (json.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          type: e.type,
          name: e.conditions
        })).filter(l => 
          nodes.some(n => n.id === l.source) && 
          nodes.some(n => n.id === l.target)
        );

        setData({ nodes, links });
      });
  }, []);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000);
      graphRef.current.zoom(2, 1000);
    }
  };

  const getIconForType = (type) => {
    switch(type) {
      case 'goal': return <ShieldAlert className="w-5 h-5 text-red-500" />;
      case 'architecture': return <Cpu className="w-5 h-5 text-blue-500" />;
      case 'method': return <Network className="w-5 h-5 text-purple-500" />;
      default: return <Shield className="w-5 h-5 text-gray-500" />;
    }
  };

  const filteredNodes = search 
    ? data.nodes.filter(n => n.name.toLowerCase().includes(search.toLowerCase()))
    : [];

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden font-sans">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 shadow-sm flex flex-col z-10">
        <div className="p-4 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input 
              type="text"
              placeholder="Search concepts..."
              className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {search && filteredNodes.map(node => (
            <div 
              key={node.id}
              className="p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-50 flex items-start gap-3"
              onClick={() => handleNodeClick(node)}
            >
              <div className="mt-0.5">{getIconForType(node.type)}</div>
              <div>
                <div className="font-medium text-sm text-gray-900">{node.name}</div>
                <div className="text-xs text-gray-500 truncate">{node.type}</div>
              </div>
            </div>
          ))}
          {!search && (
            <div className="p-8 text-center text-gray-500">
              <Shield className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p className="text-sm">Search or explore the graph to navigate AI security concepts.</p>
            </div>
          )}
        </div>
      </div>

      {/* Main Graph Area */}
      <div className="flex-1 relative">
        <ForceGraph2D
          ref={graphRef}
          graphData={data}
          nodeLabel="name"
          nodeColor={node => {
            if (selectedNode && selectedNode.id === node.id) return '#3b82f6';
            if (hoverNode && hoverNode.id === node.id) return '#60a5fa';
            switch(node.type) {
              case 'goal': return '#ef4444';
              case 'attack': return '#f97316';
              case 'architecture': return '#3b82f6';
              case 'concept': return '#10b981';
              case 'method': return '#8b5cf6';
              default: return '#9ca3af';
            }
          }}
          nodeRelSize={6}
          linkColor={() => '#e5e7eb'}
          linkWidth={1.5}
          onNodeClick={handleNodeClick}
          onNodeHover={setHoverNode}
          d3VelocityDecay={0.3}
        />

        {/* Floating Details Panel */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-6 right-6 w-96 bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden"
            >
              <div className="p-5">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2">
                    {getIconForType(selectedNode.type)}
                    <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                      {selectedNode.type}
                    </span>
                  </div>
                  <button 
                    onClick={() => setSelectedNode(null)}
                    className="p-1 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                <h3 className="text-xl font-bold text-gray-900 mb-2">{selectedNode.name}</h3>
                <p className="text-sm text-gray-600 mb-4 leading-relaxed">
                  {selectedNode.summary || 'No summary available.'}
                </p>

                <div className="flex gap-2">
                  <a 
                    href={`/nodes/${selectedNode.id}`}
                    className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    Read Article <ChevronRight className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

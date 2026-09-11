import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { GraphApp } from './GraphApp';

const container = document.getElementById('graph-root');
if (container) {
  createRoot(container).render(
    <StrictMode>
      <GraphApp />
    </StrictMode>
  );
}

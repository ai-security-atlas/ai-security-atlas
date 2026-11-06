import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { GraphApp } from './GraphApp';

const container = document.getElementById('graph-root');
if (container) {
  // On /nodes/<id>/ the app takes over a server-rendered page (layouts/node/single.html):
  // drop that page and switch the body to the app's full-screen layout.
  if (document.body.classList.contains('docpage')) {
    for (const el of Array.from(document.body.children)) if (el !== container) el.remove();
    document.body.className = 'm-0 p-0 overflow-hidden';
  }
  (window as any).__atlasMounted = true;
  createRoot(container).render(
    <StrictMode>
      <GraphApp />
    </StrictMode>
  );
}

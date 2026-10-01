import { createRoot } from 'react-dom/client';
// Шрифты дизайн-системы лежат в сборке — страница не зависит от внешних CDN.
import '@fontsource/golos-text/400.css';
import '@fontsource/golos-text/500.css';
import '@fontsource/golos-text/600.css';
import '@fontsource/golos-text/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import './ds/styles.css';
import { App } from './App';

createRoot(document.getElementById('root')!).render(<App />);

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Сборка кладётся в web/dist — её отдаёт FastAPI (app/main.py).
// В режиме разработки (npm run dev) запросы /api уходят на работающий сервис.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8010' } },
});

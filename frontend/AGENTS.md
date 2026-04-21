# Frontend Agent Instructions

## Stack
- Next.js 15 (App Router), TypeScript, Tailwind CSS v3
- Backend FastAPI en http://localhost:8000 (proxy via /api/* rewrites)

## Rutas clave
- app/page.tsx — homepage (redirige a /chat)
- app/chat/page.tsx — UI principal del chat
- components/ — componentes reutilizables
- hooks/useChat.ts — lógica de comunicación con FastAPI
- lib/api.ts — cliente HTTP base
- lib/types.ts — tipos TypeScript compartidos

## Comandos
- `npm run dev` — servidor de desarrollo (puerto 3000)
- `npm run build` — build de producción
- `npm run lint` — ESLint

## Restricciones
- No usar `output: "export"` en next.config.ts (incompatible con rewrites)
- No mezclar Tailwind v3 y v4
- El backend corre en puerto 8000, el proxy está configurado en next.config.ts

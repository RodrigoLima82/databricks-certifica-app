/*
 * Service worker mínimo e conservador para o Certifica.
 *
 * Objetivo: satisfazer o critério de "app instalável" (PWA) SEM introduzir
 * cache que possa servir HTML/JS desatualizado ou interferir com o gateway
 * OAuth do Databricks Apps e as chamadas /api.
 *
 * Estratégia: network-only (passthrough). Não cacheia nada. Se offline, o
 * navegador simplesmente falha como faria sem SW — comportamento previsível.
 * Assim ganhamos "Adicionar à tela de início" + display standalone sem risco
 * de stale content nem de quebrar auth.
 */
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // passthrough explícito — necessário existir um handler de fetch para a
  // instalabilidade, mas sem cache para evitar servir conteúdo velho.
  event.respondWith(fetch(event.request));
});

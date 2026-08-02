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
  // Só interceptamos GET do mesmo origin. Qualquer outra coisa (inclusive o
  // redirect do gateway OAuth do Databricks para outro origin) não é tocada:
  // deixamos o navegador seguir seu fluxo normal, evitando erros de CORS.
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) {
    return;
  }
  // Passthrough sem cache; se a rede falhar, não propaga como erro não tratado.
  event.respondWith(fetch(req).catch(() => Response.error()));
});

import { vi } from 'vitest';

import type { Analysis, Conflict, Product, Routine } from '../lib/api';

export const analysis: Analysis = {
  id: 7,
  ingredient_text: 'Aqua, Retinol, Mystery',
  skin_type: 'sensitive',
  ai_status: 'fallback',
  ingredients: [
    {
      name: 'water',
      function: 'Solvent',
      irritant_level: 0,
      position: 0,
      matched_as: 'aqua',
      match_type: 'alias',
      likely_irritant: false,
      explanation: 'Water (solvent) dissolves the other ingredients.',
      routine_slot: 'morning',
    },
    {
      name: 'retinol',
      function: 'Retinoid',
      irritant_level: 4,
      position: 1,
      matched_as: 'retinol',
      match_type: 'exact',
      likely_irritant: true,
      explanation: 'Retinol (retinoid) speeds up cell turnover.',
      routine_slot: 'evening',
    },
  ],
  unmatched: [{ position: 2, name: 'mystery' }],
};

export const products: Product[] = [
  {
    id: 1,
    name: 'Peel',
    brand: null,
    ingredients_text: 'Glycolic Acid',
    ingredient_names: ['glycolic acid'],
  },
  {
    id: 2,
    name: 'Night serum',
    brand: 'Lab',
    ingredients_text: 'Retinol',
    ingredient_names: ['retinol'],
  },
];

export const routine: Routine = {
  id: 3,
  name: 'Night',
  skin_type: 'normal',
  items: [
    { id: 10, product_id: 1, product_name: 'Peel', slot: 'evening' },
    { id: 11, product_id: 2, product_name: 'Night serum', slot: 'evening' },
  ],
};

export const conflicts: Conflict[] = [
  {
    slot: 'evening',
    product_a: 'Peel',
    product_b: 'Night serum',
    severity: 'high',
    reason: 'Too strong together.',
  },
];

type Route = { method?: string; path: string; status?: number; body?: unknown };

/** Stub fetch with a list of routes; unmatched requests fail the test loudly. */
export function mockFetch(routes: Route[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    const method = init?.method ?? 'GET';
    const route = routes.find(
      (r) => (r.method ?? 'GET') === method && url.pathname + url.search === r.path,
    );
    if (!route) throw new Error(`Unexpected ${method} ${url.pathname}${url.search}`);
    const status = route.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(route.body ?? {}), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

// Typed client for the FastAPI service. Types mirror the Pydantic schemas in api/app/schemas.py.

export type SkinType = 'normal' | 'dry' | 'oily' | 'sensitive' | 'combination';
export type Slot = 'morning' | 'evening';

export const SKIN_TYPES: SkinType[] = ['normal', 'dry', 'oily', 'sensitive', 'combination'];

export type IngredientResult = {
  name: string;
  function: string;
  irritant_level: number;
  position: number;
  matched_as: string;
  match_type: 'exact' | 'alias' | 'fuzzy';
  likely_irritant: boolean;
  explanation: string;
  routine_slot: Slot;
};

export type Analysis = {
  id: number | null;
  ingredient_text: string;
  skin_type: SkinType;
  ingredients: IngredientResult[];
  unmatched: { position: number; name: string }[];
  ai_status: 'ai' | 'rules' | 'fallback';
};

export type LabelAnalysis = Analysis & { extracted_text: string };

export type Product = {
  id: number;
  name: string;
  brand: string | null;
  ingredients_text: string;
  ingredient_names: string[];
};

export type RoutineItem = { id: number; product_id: number; product_name: string; slot: Slot };
export type Routine = { id: number; name: string; skin_type: SkinType; items: RoutineItem[] };

export type Conflict = {
  slot: Slot;
  product_a: string;
  product_b: string;
  severity: 'low' | 'medium' | 'high';
  reason: string;
};

export type UploadTicket = {
  object_name: string;
  upload_url: string;
  method: 'PUT';
  headers: Record<string, string>;
  expires_in_seconds: number;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Server components run inside the web container, where the API is reachable by service name.
function baseUrl(): string {
  if (typeof window === 'undefined' && process.env.API_INTERNAL_BASE_URL) {
    return process.env.API_INTERNAL_BASE_URL;
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
}

/** Turn an RFC 7807 problem document into a readable message. */
export function problemMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { loc?: unknown[]; msg?: string }) => {
          const field = d.loc?.at(-1);
          return field ? `${String(field).replaceAll('_', ' ')}: ${d.msg}` : d.msg;
        })
        .join('; ');
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    cache: 'no-store',
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(
      problemMessage(body, `Request failed (${response.status})`),
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

export const api = {
  analyse: (ingredient_text: string, skin_type: SkinType) =>
    request<Analysis>('/analyses', post({ ingredient_text, skin_type })),
  analysis: (id: number) => request<Analysis>(`/analyses/${id}`),

  products: () => request<Product[]>('/products'),
  createProduct: (product: { name: string; brand: string | null; ingredients_text: string }) =>
    request<Product>('/products', post(product)),
  deleteProduct: (id: number) => request<void>(`/products/${id}`, { method: 'DELETE' }),

  routines: () => request<Routine[]>('/routines'),
  createRoutine: (routine: { name: string; skin_type: SkinType }) =>
    request<Routine>('/routines', post(routine)),
  addItem: (routineId: number, item: { product_id: number; slot: Slot }) =>
    request<Routine>(`/routines/${routineId}/items`, post(item)),
  removeItem: (routineId: number, itemId: number) =>
    request<void>(`/routines/${routineId}/items/${itemId}`, { method: 'DELETE' }),
  conflicts: (routineId: number) => request<Conflict[]>(`/routines/${routineId}/conflicts`),

  /** Get an upload URL, PUT the image to it, then ask the API to read and analyse it. */
  analyseLabel: async (file: File, skin_type: SkinType): Promise<LabelAnalysis> => {
    const ticket = await request<UploadTicket>(
      '/labels/upload-url',
      post({ content_type: file.type }),
    );
    const upload = await fetch(ticket.upload_url, {
      method: ticket.method,
      headers: ticket.headers,
      body: file,
    });
    if (!upload.ok) throw new ApiError('Image upload failed', upload.status);
    const query = new URLSearchParams({ object_name: ticket.object_name });
    return request<LabelAnalysis>(`/labels/analyses?${query}`, post({ skin_type }));
  },
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong';
}

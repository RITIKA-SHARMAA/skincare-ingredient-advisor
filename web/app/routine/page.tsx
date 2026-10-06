'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  api,
  errorMessage,
  type Conflict,
  type Product,
  type Routine,
  type Slot,
} from '../../lib/api';

const SEVERITY_STYLE: Record<Conflict['severity'], string> = {
  high: 'border-red-300 bg-red-50',
  medium: 'border-amber-300 bg-amber-50',
  low: 'border-stone-300 bg-stone-50',
};

export default function RoutinePage() {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [routineId, setRoutineId] = useState<number | null>(null);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [newName, setNewName] = useState('My routine');
  const [productId, setProductId] = useState('');
  const [slot, setSlot] = useState<Slot>('evening');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const routine = routines.find((r) => r.id === routineId) ?? null;

  const refresh = useCallback(async (selectId?: number) => {
    const [allRoutines, allProducts] = await Promise.all([api.routines(), api.products()]);
    setRoutines(allRoutines);
    setProducts(allProducts);
    const id = selectId ?? allRoutines[0]?.id ?? null;
    setRoutineId(id);
    setConflicts(id ? await api.conflicts(id) : []);
  }, []);

  useEffect(() => {
    refresh()
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  }, [refresh]);

  const run = async (action: () => Promise<number | undefined>) => {
    setError('');
    try {
      await refresh(await action());
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const createRoutine = (event: React.FormEvent) => {
    event.preventDefault();
    void run(async () => (await api.createRoutine({ name: newName, skin_type: 'normal' })).id);
  };

  const addProduct = (event: React.FormEvent) => {
    event.preventDefault();
    if (!routine || !productId) return setError('Choose a product to add.');
    void run(async () => {
      await api.addItem(routine.id, { product_id: Number(productId), slot });
      setProductId('');
      return routine.id;
    });
  };

  const removeItem = (itemId: number) => {
    if (!routine) return;
    void run(async () => {
      await api.removeItem(routine.id, itemId);
      return routine.id;
    });
  };

  if (loading) return <p>Loading routines…</p>;

  return (
    <section>
      <h1 className="text-3xl font-bold">My routine</h1>
      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-red-800">
          {error}
        </p>
      )}

      <form onSubmit={createRoutine} className="mt-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="routine-name" className="block text-sm font-semibold">
            New routine name
          </label>
          <input
            id="routine-name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="focus-ring mt-1 rounded-lg border p-2"
          />
        </div>
        <button type="submit" className="focus-ring rounded-lg bg-teal-800 px-4 py-2 text-white">
          Create routine
        </button>
        {routines.length > 1 && (
          <div>
            <label htmlFor="routine-select" className="block text-sm font-semibold">
              Showing
            </label>
            <select
              id="routine-select"
              value={routineId ?? ''}
              onChange={(e) => void run(async () => Number(e.target.value))}
              className="focus-ring mt-1 rounded-lg border p-2"
            >
              {routines.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </form>

      {routine && (
        <div className="mt-6 rounded-2xl border bg-white p-5">
          <h2 className="text-xl font-bold">{routine.name}</h2>
          <form onSubmit={addProduct} className="mt-4 flex flex-wrap gap-2">
            <label htmlFor="product-select" className="sr-only">
              Product
            </label>
            <select
              id="product-select"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              className="focus-ring rounded-lg border p-2"
            >
              <option value="">Select a saved product</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <label htmlFor="slot-select" className="sr-only">
              Slot
            </label>
            <select
              id="slot-select"
              value={slot}
              onChange={(e) => setSlot(e.target.value as Slot)}
              className="focus-ring rounded-lg border p-2"
            >
              <option value="morning">Morning</option>
              <option value="evening">Evening</option>
            </select>
            <button type="submit" className="focus-ring rounded-lg border px-4 py-2">
              Add to routine
            </button>
          </form>

          {(['morning', 'evening'] as const).map((s) => {
            const items = routine.items.filter((i) => i.slot === s);
            return (
              <div key={s} className="mt-5">
                <h3 className="font-semibold capitalize">{s}</h3>
                {items.length === 0 ? (
                  <p className="text-sm text-stone-500">Nothing yet.</p>
                ) : (
                  <ul className="mt-2 space-y-2">
                    {items.map((item) => (
                      <li key={item.id} className="flex items-center justify-between gap-2">
                        <span>{item.product_name}</span>
                        <button
                          type="button"
                          onClick={() => removeItem(item.id)}
                          className="focus-ring rounded border px-2 py-1 text-sm"
                          aria-label={`Remove ${item.product_name}`}
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}

          <h3 className="mt-6 font-semibold">Conflicts</h3>
          {conflicts.length === 0 ? (
            <p className="text-sm text-stone-600">No conflicts found in this routine.</p>
          ) : (
            <ul className="mt-2 space-y-2" aria-label="Conflicts">
              {conflicts.map((c) => (
                <li
                  key={`${c.slot}-${c.product_a}-${c.product_b}`}
                  className={`rounded-xl border p-3 text-sm ${SEVERITY_STYLE[c.severity]}`}
                >
                  <strong>
                    {c.product_a} + {c.product_b}
                  </strong>{' '}
                  ({c.slot}, {c.severity}): {c.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

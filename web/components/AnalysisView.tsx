'use client';

import Link from 'next/link';
import { useState } from 'react';

import { api, errorMessage, type Analysis } from '../lib/api';

const STATUS_TEXT: Record<Analysis['ai_status'], string> = {
  ai: 'Explanations written by Gemini and checked against the catalogue.',
  rules: 'Explanations from the built-in catalogue rules.',
  fallback: 'Gemini output failed validation, so catalogue rules were used instead.',
};

export function SaveProduct({ analysis }: { analysis: Analysis }) {
  const [name, setName] = useState('');
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState('');

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    if (!name.trim()) return setError('Give the product a name.');
    try {
      const product = await api.createProduct({
        name: name.trim(),
        brand: null,
        ingredients_text: analysis.ingredient_text,
      });
      setSaved(product.name);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  if (saved) {
    return (
      <p role="status" className="rounded-xl border bg-white p-4">
        Saved “{saved}”.{' '}
        <Link className="focus-ring underline" href="/routine">
          Add it to a routine
        </Link>
      </p>
    );
  }
  return (
    <form onSubmit={save} className="flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4">
      <div className="grow">
        <label htmlFor="product-name" className="block text-sm font-semibold">
          Save as product
        </label>
        <input
          id="product-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Product name"
          className="focus-ring mt-1 w-full rounded-lg border p-2"
        />
      </div>
      <button type="submit" className="focus-ring rounded-lg bg-teal-800 px-4 py-2 text-white">
        Save product
      </button>
      {error && (
        <p role="alert" className="w-full text-sm text-red-700">
          {error}
        </p>
      )}
    </form>
  );
}

export default function AnalysisView({ analysis }: { analysis: Analysis }) {
  return (
    <section>
      <h1 className="text-3xl font-bold">Analysis result</h1>
      <p className="mt-2 text-sm text-stone-600">
        Skin type: {analysis.skin_type}. {STATUS_TEXT[analysis.ai_status]}
      </p>
      <div className="mt-6">
        <SaveProduct analysis={analysis} />
      </div>
      <ul className="mt-6 grid gap-4" aria-label="Ingredients">
        {analysis.ingredients.map((item) => (
          <li key={item.position} className="rounded-2xl border bg-white p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="font-bold capitalize">{item.name}</h2>
              <span className="text-sm text-stone-600">
                {item.function} · {item.routine_slot}
              </span>
            </div>
            {item.match_type !== 'exact' && (
              <p className="mt-1 text-xs text-stone-500">
                Listed as “{item.matched_as}” ({item.match_type} match)
              </p>
            )}
            <p className="mt-2 text-stone-700">{item.explanation}</p>
            <p className="mt-3 text-sm">
              Irritant level {item.irritant_level}/5
              {item.likely_irritant && (
                <strong className="text-red-700"> · likely irritant for this skin type</strong>
              )}
            </p>
          </li>
        ))}
      </ul>
      {analysis.unmatched.length > 0 && (
        <aside className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h2 className="font-bold">Not in the catalogue</h2>
          <p className="mt-1 text-sm">{analysis.unmatched.map((u) => u.name).join(', ')}</p>
        </aside>
      )}
    </section>
  );
}

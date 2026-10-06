'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { api, errorMessage, SKIN_TYPES, type SkinType } from '../lib/api';

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_BYTES = 5 * 1024 * 1024;

export default function LabelUpload() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [skinType, setSkinType] = useState<SkinType>('normal');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const choose = (selected: File | undefined) => {
    setError('');
    setFile(null);
    if (!selected) return;
    if (!ACCEPTED.includes(selected.type)) return setError('Use a JPEG, PNG or WebP photo.');
    if (selected.size > MAX_BYTES) return setError('Photos must be 5 MB or smaller.');
    setFile(selected);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return setError('Choose a photo of the ingredient list first.');
    setBusy(true);
    setError('');
    try {
      const analysis = await api.analyseLabel(file, skinType);
      router.push(`/analyses/${analysis.id}`);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="label-photo" className="font-semibold">
          Label photo
        </label>
        <input
          id="label-photo"
          type="file"
          accept={ACCEPTED.join(',')}
          onChange={(e) => choose(e.target.files?.[0])}
          className="focus-ring mt-2 block w-full rounded-xl border bg-white p-3 text-sm"
        />
      </div>
      <div>
        <label htmlFor="label-skin-type" className="font-semibold">
          Skin type
        </label>
        <select
          id="label-skin-type"
          value={skinType}
          onChange={(e) => setSkinType(e.target.value as SkinType)}
          className="focus-ring mt-2 w-full rounded-xl border p-3"
        >
          {SKIN_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>
      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="focus-ring rounded-xl border border-teal-800 px-5 py-3 font-semibold text-teal-900 disabled:opacity-50"
      >
        {busy ? 'Reading label…' : 'Read label and analyse'}
      </button>
    </form>
  );
}

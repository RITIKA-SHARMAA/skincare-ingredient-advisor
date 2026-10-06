'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { api, errorMessage, SKIN_TYPES } from '../lib/api';

const schema = z.object({
  ingredientText: z
    .string()
    .trim()
    .min(2, 'Paste at least one ingredient')
    .max(10_000, 'That list is too long'),
  skinType: z.enum(SKIN_TYPES),
});

type FormValues = z.infer<typeof schema>;

export default function AnalyseForm() {
  const router = useRouter();
  const [error, setError] = useState('');
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { ingredientText: '', skinType: 'normal' },
  });

  const onSubmit = async (values: FormValues) => {
    setError('');
    try {
      const analysis = await api.analyse(values.ingredientText, values.skinType);
      router.push(`/analyses/${analysis.id}`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div>
        <label htmlFor="ingredient-text" className="font-semibold">
          Ingredient list
        </label>
        <textarea
          id="ingredient-text"
          {...register('ingredientText')}
          aria-invalid={errors.ingredientText ? true : undefined}
          aria-describedby={errors.ingredientText ? 'ingredient-text-error' : undefined}
          className="focus-ring mt-2 min-h-44 w-full rounded-xl border p-3"
          placeholder="Water, Glycerin, Niacinamide, Salicylic Acid..."
        />
        {errors.ingredientText && (
          <p id="ingredient-text-error" className="text-sm text-red-700">
            {errors.ingredientText.message}
          </p>
        )}
      </div>
      <div>
        <label htmlFor="skin-type" className="font-semibold">
          Skin type
        </label>
        <select
          id="skin-type"
          {...register('skinType')}
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
        disabled={isSubmitting}
        className="focus-ring rounded-xl bg-teal-800 px-5 py-3 font-semibold text-white disabled:opacity-50"
      >
        {isSubmitting ? 'Analysing…' : 'Analyse ingredients'}
      </button>
    </form>
  );
}

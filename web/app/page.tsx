import Link from 'next/link';

export default function Home() {
  return (
    <section className="py-12">
      <p className="mb-3 text-sm font-semibold tracking-wide text-teal-700 uppercase">
        Ingredient intelligence
      </p>
      <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
        Understand what is in your skincare.
      </h1>
      <p className="mt-5 max-w-2xl text-lg text-stone-600">
        Paste an ingredient list or upload a label photo, read plain-language explanations, and
        check how products fit together in a routine.
      </p>
      <Link
        className="focus-ring mt-8 inline-block rounded-xl bg-teal-800 px-5 py-3 font-semibold text-white"
        href="/analyse"
      >
        Analyse a product
      </Link>
    </section>
  );
}

import Link from 'next/link';

export default function NotFound() {
  return (
    <section>
      <h1 className="text-3xl font-bold">Not found</h1>
      <p className="mt-3">
        That page does not exist.{' '}
        <Link className="focus-ring underline" href="/analyse">
          Analyse a product
        </Link>
      </p>
    </section>
  );
}

import { api, type Product } from '../../lib/api';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Product catalogue | Skincare Ingredient Advisor' };

export default async function ProductsPage() {
  let products: Product[] = [];
  let failed = false;
  try {
    products = await api.products();
  } catch {
    failed = true;
  }

  return (
    <section>
      <h1 className="text-3xl font-bold">Product catalogue</h1>
      <p className="mt-2 text-stone-600">
        Products you saved from an analysis, with the catalogue ingredients they matched.
      </p>
      {failed && (
        <p role="alert" className="mt-6 rounded-xl border border-red-300 bg-red-50 p-4">
          The catalogue could not be loaded. Is the API running?
        </p>
      )}
      {!failed && products.length === 0 && (
        <p className="mt-6 rounded-xl border bg-white p-5">No products saved yet.</p>
      )}
      <ul className="mt-6 grid gap-4 sm:grid-cols-2">
        {products.map((product) => (
          <li key={product.id} className="rounded-2xl border bg-white p-5">
            <h2 className="font-bold">{product.name}</h2>
            {product.brand && <p className="text-sm text-stone-500">{product.brand}</p>}
            <p className="mt-3 text-sm text-stone-700">
              {product.ingredient_names.length} matched: {product.ingredient_names.join(', ')}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

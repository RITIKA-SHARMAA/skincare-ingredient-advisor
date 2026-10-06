import AnalyseForm from '../../components/AnalyseForm';
import LabelUpload from '../../components/LabelUpload';

export const metadata = { title: 'Analyse ingredients | Skincare Ingredient Advisor' };

export default function AnalysePage() {
  return (
    <section className="grid gap-10 lg:grid-cols-[3fr_2fr]">
      <div>
        <h1 className="text-3xl font-bold">Analyse ingredients</h1>
        <p className="mt-2 mb-7 text-stone-600">
          Paste the ingredient list from the back of the product.
        </p>
        <AnalyseForm />
      </div>
      <div className="rounded-2xl border bg-white p-5">
        <h2 className="text-xl font-bold">Or upload a label photo</h2>
        <p className="mt-2 mb-5 text-sm text-stone-600">
          Gemini reads the ingredient list from the photo. Needs the Vertex AI provider.
        </p>
        <LabelUpload />
      </div>
    </section>
  );
}

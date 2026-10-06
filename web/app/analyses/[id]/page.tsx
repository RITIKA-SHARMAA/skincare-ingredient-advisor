import Link from 'next/link';
import { notFound } from 'next/navigation';

import AnalysisView from '../../../components/AnalysisView';
import { api, ApiError } from '../../../lib/api';

export const dynamic = 'force-dynamic';

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const numericId = Number(id);
  if (!Number.isInteger(numericId)) notFound();
  try {
    const analysis = await api.analysis(numericId);
    return <AnalysisView analysis={analysis} />;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    return (
      <p role="alert">
        Could not load this analysis.{' '}
        <Link className="underline" href="/analyse">
          Try again
        </Link>
      </p>
    );
  }
}

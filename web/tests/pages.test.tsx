import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import RoutinePage from '../app/routine/page';
import AnalysisView from '../components/AnalysisView';
import { analysis, conflicts, mockFetch, products, routine } from './fixtures';

describe('AnalysisView', () => {
  it('shows each ingredient, how it matched, irritant flags and unmatched names', () => {
    render(<AnalysisView analysis={analysis} />);
    const items = within(screen.getByRole('list', { name: 'Ingredients' })).getAllByRole(
      'listitem',
    );
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Listed as “aqua” (alias match)');
    expect(items[1]).toHaveTextContent('likely irritant for this skin type');
    expect(screen.getByText(/failed validation/)).toBeInTheDocument();
    expect(screen.getByText('mystery')).toBeInTheDocument();
  });

  it('saves the analysed list as a product', async () => {
    const fetchMock = mockFetch([
      {
        method: 'POST',
        path: '/products',
        status: 201,
        body: { ...products[0], name: 'My serum' },
      },
    ]);
    render(<AnalysisView analysis={analysis} />);
    await userEvent.click(screen.getByRole('button', { name: 'Save product' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Give the product a name.');
    await userEvent.type(screen.getByLabelText('Save as product'), 'My serum');
    await userEvent.click(screen.getByRole('button', { name: 'Save product' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Saved “My serum”');
    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(body.ingredients_text).toBe(analysis.ingredient_text);
  });
});

describe('RoutinePage', () => {
  it('loads the routine with its slots and conflicts', async () => {
    mockFetch([
      { path: '/routines', body: [routine] },
      { path: '/products', body: products },
      { path: '/routines/3/conflicts', body: conflicts },
    ]);
    render(<RoutinePage />);
    expect(await screen.findByRole('heading', { name: 'Night' })).toBeInTheDocument();
    const list = screen.getByRole('list', { name: 'Conflicts' });
    expect(list).toHaveTextContent('Peel + Night serum (evening, high): Too strong together.');
    expect(screen.getByRole('button', { name: 'Remove Peel' })).toBeInTheDocument();
  });

  it('adds a product to the chosen slot', async () => {
    const fetchMock = mockFetch([
      { path: '/routines', body: [{ ...routine, items: [] }] },
      { path: '/products', body: products },
      { path: '/routines/3/conflicts', body: [] },
      { method: 'POST', path: '/routines/3/items', status: 201, body: routine },
    ]);
    render(<RoutinePage />);
    await screen.findByText('No conflicts found in this routine.');
    await userEvent.selectOptions(screen.getByLabelText('Product'), '2');
    await userEvent.selectOptions(screen.getByLabelText('Slot'), 'morning');
    await userEvent.click(screen.getByRole('button', { name: 'Add to routine' }));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
      expect(JSON.parse(String(post?.[1]?.body))).toEqual({ product_id: 2, slot: 'morning' });
    });
  });

  it('shows API errors, such as adding a product twice', async () => {
    mockFetch([
      { path: '/routines', body: [routine] },
      { path: '/products', body: products },
      { path: '/routines/3/conflicts', body: conflicts },
      {
        method: 'POST',
        path: '/routines/3/items',
        status: 409,
        body: { detail: 'Product is already in this routine' },
      },
    ]);
    render(<RoutinePage />);
    await screen.findByRole('heading', { name: 'Night' });
    await userEvent.selectOptions(screen.getByLabelText('Product'), '1');
    await userEvent.click(screen.getByRole('button', { name: 'Add to routine' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('already in this routine');
  });

  it('reports a load failure', async () => {
    mockFetch([]);
    render(<RoutinePage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unexpected GET /routines');
  });
});

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import AnalyseForm from '../components/AnalyseForm';
import LabelUpload from '../components/LabelUpload';
import Home from '../app/page';
import { analysis, mockFetch } from './fixtures';
import { push } from './setup';

describe('Home', () => {
  it('links to the analyse page', () => {
    render(<Home />);
    expect(screen.getByRole('link', { name: /analyse a product/i })).toHaveAttribute(
      'href',
      '/analyse',
    );
  });
});

describe('AnalyseForm', () => {
  it('shows a validation message instead of calling the API', async () => {
    const fetchMock = mockFetch([]);
    render(<AnalyseForm />);
    await userEvent.click(screen.getByRole('button', { name: /analyse ingredients/i }));
    expect(await screen.findByText('Paste at least one ingredient')).toBeInTheDocument();
    expect(screen.getByLabelText('Ingredient list')).toHaveAttribute('aria-invalid', 'true');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('submits the list and skin type, then opens the result', async () => {
    const fetchMock = mockFetch([
      { method: 'POST', path: '/analyses', status: 201, body: analysis },
    ]);
    render(<AnalyseForm />);
    await userEvent.type(screen.getByLabelText('Ingredient list'), 'Aqua, Retinol');
    await userEvent.selectOptions(screen.getByLabelText('Skin type'), 'sensitive');
    await userEvent.click(screen.getByRole('button', { name: /analyse ingredients/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/analyses/7'));
    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(body).toEqual({ ingredient_text: 'Aqua, Retinol', skin_type: 'sensitive' });
  });

  it('shows the API error inline', async () => {
    mockFetch([
      {
        method: 'POST',
        path: '/analyses',
        status: 413,
        body: { detail: 'at most 100 ingredients per request' },
      },
    ]);
    render(<AnalyseForm />);
    await userEvent.type(screen.getByLabelText('Ingredient list'), 'Water');
    await userEvent.click(screen.getByRole('button', { name: /analyse ingredients/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('at most 100 ingredients');
    expect(push).not.toHaveBeenCalled();
  });
});

describe('LabelUpload', () => {
  it('rejects files that are not images', async () => {
    render(<LabelUpload />);
    const pdf = new File(['x'], 'label.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText('Label photo'), pdf, { applyAccept: false });
    expect(screen.getByRole('alert')).toHaveTextContent('Use a JPEG, PNG or WebP photo.');
  });

  it('asks for a photo before submitting', async () => {
    render(<LabelUpload />);
    await userEvent.click(screen.getByRole('button', { name: /read label/i }));
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a photo');
  });

  it('shows the server message when label reading is unavailable', async () => {
    mockFetch([
      {
        method: 'POST',
        path: '/labels/upload-url',
        status: 201,
        body: {
          object_name: 'labels/a.png',
          upload_url: 'http://localhost:8000/labels/local/a.png',
          method: 'PUT',
          headers: {},
        },
      },
      { method: 'PUT', path: '/labels/local/a.png', status: 204 },
      {
        method: 'POST',
        path: '/labels/analyses?object_name=labels%2Fa.png',
        status: 503,
        body: { detail: 'Label reading needs LLM_PROVIDER=vertex' },
      },
    ]);
    render(<LabelUpload />);
    const png = new File(['x'], 'label.png', { type: 'image/png' });
    await userEvent.upload(screen.getByLabelText('Label photo'), png);
    await userEvent.click(screen.getByRole('button', { name: /read label/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('LLM_PROVIDER=vertex');
  });
});

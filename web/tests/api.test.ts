import { describe, expect, it } from 'vitest';

import { api, ApiError, problemMessage } from '../lib/api';
import { mockFetch } from './fixtures';

describe('problemMessage', () => {
  it('uses a string detail', () => {
    expect(problemMessage({ detail: 'Product not found' }, 'x')).toBe('Product not found');
  });

  it('joins validation errors with readable field names', () => {
    const body = {
      detail: [
        { loc: ['body', 'ingredient_text'], msg: 'too short' },
        { loc: ['body', 'skin_type'], msg: 'bad value' },
      ],
    };
    expect(problemMessage(body, 'x')).toBe('ingredient text: too short; skin type: bad value');
  });

  it('falls back when the body is not a problem document', () => {
    expect(problemMessage(null, 'fallback')).toBe('fallback');
  });
});

describe('api client', () => {
  it('throws ApiError with the problem detail and status', async () => {
    mockFetch([{ path: '/analyses/9', status: 404, body: { detail: 'Analysis not found' } }]);
    await expect(api.analysis(9)).rejects.toEqual(new ApiError('Analysis not found', 404));
  });

  it('returns undefined for 204 responses', async () => {
    mockFetch([{ method: 'DELETE', path: '/products/1', status: 204 }]);
    await expect(api.deleteProduct(1)).resolves.toBeUndefined();
  });

  it('uploads a label to the signed URL before asking for the analysis', async () => {
    const fetchMock = mockFetch([
      {
        method: 'POST',
        path: '/labels/upload-url',
        status: 201,
        body: {
          object_name: 'labels/abc.png',
          upload_url: 'https://storage.example/labels/abc.png?sig=1',
          method: 'PUT',
          headers: { 'Content-Type': 'image/png' },
          expires_in_seconds: 600,
        },
      },
      { method: 'PUT', path: '/labels/abc.png?sig=1', status: 200 },
      {
        method: 'POST',
        path: '/labels/analyses?object_name=labels%2Fabc.png',
        status: 201,
        body: { id: 5 },
      },
    ]);
    const file = new File(['x'], 'label.png', { type: 'image/png' });
    await expect(api.analyseLabel(file, 'dry')).resolves.toEqual({ id: 5 });
    const calls = fetchMock.mock.calls.map(([url, init]) => `${init?.method} ${String(url)}`);
    expect(calls).toEqual([
      'POST http://localhost:8000/labels/upload-url',
      'PUT https://storage.example/labels/abc.png?sig=1',
      'POST http://localhost:8000/labels/analyses?object_name=labels%2Fabc.png',
    ]);
  });

  it('stops when the upload itself fails', async () => {
    mockFetch([
      {
        method: 'POST',
        path: '/labels/upload-url',
        status: 201,
        body: {
          object_name: 'labels/a.png',
          upload_url: 'https://s.example/a',
          method: 'PUT',
          headers: {},
        },
      },
      { method: 'PUT', path: '/a', status: 403 },
    ]);
    const file = new File(['x'], 'label.png', { type: 'image/png' });
    await expect(api.analyseLabel(file, 'dry')).rejects.toThrow('Image upload failed');
  });
});

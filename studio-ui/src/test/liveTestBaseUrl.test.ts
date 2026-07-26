import { describe, expect, it, vi } from 'vitest';

import { requireLiveTestBaseUrl } from './liveTestBaseUrl';

describe('requireLiveTestBaseUrl', () => {
  it.each([
    ['http://127.0.0.1:80', 'http://127.0.0.1'],
    ['http://127.0.0.1:8000', 'http://127.0.0.1:8000'],
    ['http://localhost:80', 'http://localhost'],
    ['http://localhost:8000', 'http://localhost:8000'],
    ['http://[::1]:80', 'http://[::1]'],
    ['http://[::1]:8000', 'http://[::1]:8000'],
  ])('accepts local live API URL %s', (rawBaseUrl, expected) => {
    expect(requireLiveTestBaseUrl(rawBaseUrl)).toBe(expected);
  });

  it.each([
    'https://127.0.0.1:8000',
    'http://example.com:8000',
    'http://192.0.2.1:8000',
    'http://127.0.0.2:8000',
    'http://user:pass@127.0.0.1:8000',
    'http://user:pass@127.0.0.1:80',
    'http://127.0.0.1',
    'http://localhost',
    'http://[::1]',
    'http://127.0.0.1:8000/api',
    'http://127.0.0.1:80/api',
    'http://127.0.0.1:8000?x=1',
    'http://127.0.0.1:80?x=1',
    'http://127.0.0.1:8000/#fragment',
    'http://127.0.0.1:80/#fragment',
    'http://127.0.0.1:abc',
    'http://127.0.0.1:65536',
    'file:///tmp/api',
    ['C:', 'tmp', 'api'].join('\\'),
    ' http://127.0.0.1:8000',
    'http://127.0.0.1:8000 ',
    'not a url',
  ])('rejects unsafe live API URL %s before network setup', (rawBaseUrl) => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    expect(() => requireLiveTestBaseUrl(rawBaseUrl)).toThrowError(
      'KURGU_STUDIO_API_BASE_URL must be an HTTP loopback URL with an explicit port.',
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('keeps missing-environment guidance explicit', () => {
    expect(() => requireLiveTestBaseUrl(undefined)).toThrowError(
      'KURGU_STUDIO_API_BASE_URL is required for the live test.',
    );
  });

  it('does not echo rejected raw URLs in the public error', () => {
    const rawBaseUrl = 'https://example.com:8443/private?x=1';

    expect(() => requireLiveTestBaseUrl(rawBaseUrl)).toThrowError(
      expect.objectContaining({
        message:
          'KURGU_STUDIO_API_BASE_URL must be an HTTP loopback URL with an explicit port.',
      }),
    );
  });
});

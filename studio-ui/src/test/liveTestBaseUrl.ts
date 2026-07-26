const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '::1', '[::1]']);

const REQUIRED_MESSAGE =
  'KURGU_STUDIO_API_BASE_URL is required for the live test.';
const INVALID_MESSAGE =
  'KURGU_STUDIO_API_BASE_URL must be an HTTP loopback URL with an explicit port.';

export function requireLiveTestBaseUrl(rawBaseUrl: string | undefined): string {
  if (rawBaseUrl === undefined || rawBaseUrl === '') {
    throw new Error(REQUIRED_MESSAGE);
  }
  if (rawBaseUrl.trim() !== rawBaseUrl) {
    throw new Error(INVALID_MESSAGE);
  }

  let parsed: URL;
  try {
    parsed = new URL(rawBaseUrl);
  } catch {
    throw new Error(INVALID_MESSAGE);
  }

  if (
    parsed.protocol !== 'http:' ||
    !LOOPBACK_HOSTS.has(parsed.hostname) ||
    !hasExplicitPort(rawBaseUrl, parsed) ||
    parsed.username !== '' ||
    parsed.password !== '' ||
    parsed.pathname !== '/' ||
    parsed.search !== '' ||
    parsed.hash !== ''
  ) {
    throw new Error(INVALID_MESSAGE);
  }

  return parsed.origin;
}

function hasExplicitPort(rawBaseUrl: string, parsed: URL): boolean {
  const authority = getRawAuthority(rawBaseUrl, parsed);
  const hostPort = authority.slice(authority.lastIndexOf('@') + 1);

  if (hostPort.startsWith('[')) {
    const closingBracket = hostPort.indexOf(']');
    if (closingBracket === -1) {
      return false;
    }
    return isPortLiteral(hostPort.slice(closingBracket + 1));
  }

  const portSeparator = hostPort.lastIndexOf(':');
  if (portSeparator === -1 || portSeparator === hostPort.length - 1) {
    return false;
  }
  return isPortLiteral(hostPort.slice(portSeparator));
}

function getRawAuthority(rawBaseUrl: string, parsed: URL): string {
  const authorityStart = parsed.protocol.length + '//'.length;
  const authorityAndTail = rawBaseUrl.slice(authorityStart);
  const authorityEnd = firstIndexOfAny(authorityAndTail, ['/', '?', '#']);

  if (authorityEnd === -1) {
    return authorityAndTail;
  }
  return authorityAndTail.slice(0, authorityEnd);
}

function firstIndexOfAny(value: string, needles: string[]): number {
  const indexes = needles
    .map((needle) => value.indexOf(needle))
    .filter((index) => index !== -1);

  if (indexes.length === 0) {
    return -1;
  }
  return Math.min(...indexes);
}

function isPortLiteral(portPart: string): boolean {
  return /^:[0-9]+$/.test(portPart);
}

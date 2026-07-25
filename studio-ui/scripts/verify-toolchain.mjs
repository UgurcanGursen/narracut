import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = dirname(scriptDir);
const packageJson = JSON.parse(readFileSync(join(projectRoot, 'package.json'), 'utf8'));
const lockPath = join(projectRoot, 'package-lock.json');

function fail(message) {
  console.log(JSON.stringify({ status: 'FAIL', error: message }));
  process.exit(1);
}

function assert(condition, message) {
  if (!condition) {
    fail(message);
  }
}

function exactPins(section) {
  return Object.entries(section ?? {}).map(([name, pin]) => {
    assert(typeof pin === 'string' && !/[\^~*]/.test(pin) && !pin.includes('latest'), `${name} is not exact pinned`);
    return [name, pin];
  });
}

function packageMetadata(name) {
  let packageJsonPath;
  try {
    packageJsonPath = require.resolve(`${name}/package.json`);
  } catch {
    packageJsonPath = join(projectRoot, 'node_modules', ...name.split('/'), 'package.json');
  }
  assert(existsSync(packageJsonPath), `package metadata not found for ${name}`);
  let cursor = dirname(packageJsonPath);
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = join(cursor, 'package.json');
    if (existsSync(candidate)) {
      const metadata = JSON.parse(readFileSync(candidate, 'utf8'));
      if (metadata.name === name) {
        return { metadata, path: candidate };
      }
    }
    const parent = dirname(cursor);
    if (parent === cursor) {
      break;
    }
    cursor = parent;
  }
  fail(`package metadata not found for ${name}`);
}

function verifyInstalledPins() {
  const pins = new Map([
    ...exactPins(packageJson.dependencies),
    ...exactPins(packageJson.devDependencies),
  ]);
  const versions = {};
  for (const [name, expected] of pins) {
    const { metadata } = packageMetadata(name);
    assert(metadata.version === expected, `${name}: ${metadata.version} != ${expected}`);
    versions[name] = metadata.version;
  }
  return versions;
}

async function verifyImports() {
  const react = await import('react');
  const reactDomClient = await import('react-dom/client');
  const typescript = await import('typescript');
  const vite = await import('vite');
  const reactPlugin = await import('@vitejs/plugin-react');
  const vitest = await import('vitest');
  const jsdom = await import('jsdom');
  const testingLibraryReact = await import('@testing-library/react');
  const jestDomMatchers = await import('@testing-library/jest-dom/matchers');
  const userEvent = await import('@testing-library/user-event');
  await import('@hey-api/openapi-ts');

  assert(typeof react.createElement === 'function', 'react import failed');
  assert(typeof reactDomClient.createRoot === 'function', 'react-dom/client import failed');
  assert(typeof typescript.version === 'string', 'typescript import failed');
  assert(typeof vite.createServer === 'function', 'vite API import failed');
  assert(typeof reactPlugin.default === 'function', 'vite react plugin import failed');
  assert(typeof vitest.describe === 'function', 'vitest import failed');
  assert(typeof jsdom.JSDOM === 'function', 'jsdom import failed');
  assert(typeof testingLibraryReact.render === 'function', 'testing-library/react import failed');
  assert(typeof jestDomMatchers.toBeInTheDocument === 'function', 'jest-dom matchers import failed');
  assert(typeof userEvent.default.setup === 'function', 'testing-library/user-event import failed');
}

function verifyOpenApiGeneratorCli() {
  const { metadata, path } = packageMetadata('@hey-api/openapi-ts');
  assert(metadata.bin && Object.keys(metadata.bin).length > 0, 'openapi-ts bin metadata missing');
  for (const binTarget of Object.values(metadata.bin)) {
    assert(existsSync(join(dirname(path), binTarget)), `openapi-ts bin target missing: ${binTarget}`);
  }
}

assert(process.versions.node.startsWith('24.'), `unexpected node version ${process.versions.node}`);
assert(packageJson.packageManager === 'npm@11.6.2', 'packageManager must be npm@11.6.2');
assert(existsSync(lockPath), 'package-lock.json missing');

const versions = verifyInstalledPins();
await verifyImports();
verifyOpenApiGeneratorCli();

console.log(JSON.stringify({ status: 'PASS', node: process.version, versions }, null, 2));

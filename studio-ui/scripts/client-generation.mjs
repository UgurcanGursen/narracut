import { createHash } from 'node:crypto';
import {
  mkdir,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { createClient } from '@hey-api/openapi-ts';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
export const projectRoot = dirname(scriptDirectory);
export const repositoryRoot = dirname(projectRoot);
export const canonicalOpenApiPath = join(
  repositoryRoot,
  'shared-schemas',
  'openapi',
  'openapi.json',
);
export const committedOutputPath = join(
  projectRoot,
  'src',
  'generated',
  'kurgu-api',
);

const configured = await import('../openapi-ts.config.ts');
const canonicalConfig = await configured.default;

function sha256(content) {
  return createHash('sha256').update(content).digest('hex');
}

function assertControlledOutput(outputPath, temporaryRoot) {
  const resolvedOutput = resolve(outputPath);
  if (resolvedOutput === resolve(committedOutputPath)) {
    return;
  }
  if (temporaryRoot) {
    const resolvedTemporaryRoot = resolve(temporaryRoot);
    if (
      resolvedOutput.startsWith(`${resolvedTemporaryRoot}${sep}`) &&
      resolvedOutput !== resolvedTemporaryRoot
    ) {
      return;
    }
  }
  throw new Error('Generated output path is not controlled.');
}

async function generatedFiles(root) {
  const entries = await readdir(root, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolutePath = join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await generatedFiles(absolutePath)));
    } else if (entry.isFile()) {
      files.push(absolutePath);
    } else {
      throw new Error('Generated output contains an unsupported entry.');
    }
  }
  return files.sort((left, right) =>
    relative(root, left).localeCompare(relative(root, right), 'en'),
  );
}

async function normalizeGeneratedText(outputPath) {
  for (const filePath of await generatedFiles(outputPath)) {
    const content = await readFile(filePath);
    if (content.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) {
      throw new Error('Generated output contains a UTF-8 BOM.');
    }
    const normalized = content.toString('utf8').replace(/\r\n?/g, '\n');
    await writeFile(filePath, normalized, { encoding: 'utf8' });
  }
}

export async function inventoryDirectory(root) {
  const inventory = [];
  for (const absolutePath of await generatedFiles(root)) {
    const content = await readFile(absolutePath);
    inventory.push({
      path: relative(root, absolutePath).split(sep).join('/'),
      bytes: content.length,
      sha256: sha256(content),
    });
  }
  return inventory;
}

export function aggregateInventoryHash(inventory) {
  const payload = inventory
    .map((item) => `${item.path}\0${item.bytes}\0${item.sha256}\n`)
    .join('');
  return sha256(Buffer.from(payload, 'utf8'));
}

export async function generateClientTo(outputPath, options = {}) {
  if (process.argv.length > 2) {
    throw new Error('Client generation accepts no command-line arguments.');
  }
  assertControlledOutput(outputPath, options.temporaryRoot);
  const inputStats = await stat(canonicalOpenApiPath);
  if (!inputStats.isFile()) {
    throw new Error('Canonical OpenAPI input is unavailable.');
  }
  await rm(outputPath, { recursive: true, force: true });
  await mkdir(dirname(outputPath), { recursive: true });
  await createClient({
    ...canonicalConfig,
    input: canonicalOpenApiPath,
    output: outputPath,
  });
  await normalizeGeneratedText(outputPath);
  return inventoryDirectory(outputPath);
}

export async function openApiSha256() {
  return sha256(await readFile(canonicalOpenApiPath));
}

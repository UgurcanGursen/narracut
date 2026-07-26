import { mkdtemp, readFile, rm, writeFile, cp, unlink } from 'node:fs/promises';
import { join, parse } from 'node:path';

import {
  aggregateInventoryHash,
  committedOutputPath,
  generateClientTo,
  inventoryDirectory,
  openApiSha256,
  projectRoot,
} from './client-generation.mjs';

const temporaryBase = join(parse(projectRoot).root, 'tmp');

function compareInventories(expected, actual) {
  const expectedByPath = new Map(expected.map((item) => [item.path, item]));
  const actualByPath = new Map(actual.map((item) => [item.path, item]));
  const missing = [...expectedByPath.keys()].filter(
    (path) => !actualByPath.has(path),
  );
  const extra = [...actualByPath.keys()].filter(
    (path) => !expectedByPath.has(path),
  );
  const modified = [...expectedByPath.keys()].filter((path) => {
    const candidate = actualByPath.get(path);
    const baseline = expectedByPath.get(path);
    return (
      candidate &&
      baseline &&
      (candidate.bytes !== baseline.bytes ||
        candidate.sha256 !== baseline.sha256)
    );
  });
  if (missing.length || extra.length || modified.length) {
    const error = new Error('Generated client drift detected.');
    error.drift = { missing, extra, modified };
    throw error;
  }
}

async function expectDrift(expected, candidateRoot, kind) {
  try {
    compareInventories(expected, await inventoryDirectory(candidateRoot));
  } catch (error) {
    if (
      error instanceof Error &&
      error.drift &&
      error.drift[kind].length > 0
    ) {
      return;
    }
    throw error;
  }
  throw new Error(`Generated drift negative did not fail: ${kind}.`);
}

let temporaryRoot;
try {
  if (process.argv.length > 2) {
    throw new Error('Generated client check accepts no arguments.');
  }
  temporaryRoot = await mkdtemp(join(temporaryBase, 'kurgu-client-check-'));
  const outputA = join(temporaryRoot, 'a');
  const outputB = join(temporaryRoot, 'b');
  const inventoryA = await generateClientTo(outputA, { temporaryRoot });
  const inventoryB = await generateClientTo(outputB, { temporaryRoot });
  const committed = await inventoryDirectory(committedOutputPath);
  compareInventories(inventoryA, inventoryB);
  compareInventories(inventoryA, committed);

  const firstFile = inventoryA[0].path;

  const missingRoot = join(temporaryRoot, 'negative-missing');
  await cp(outputA, missingRoot, { recursive: true });
  await unlink(join(missingRoot, ...firstFile.split('/')));
  await expectDrift(inventoryA, missingRoot, 'missing');

  const extraRoot = join(temporaryRoot, 'negative-extra');
  await cp(outputA, extraRoot, { recursive: true });
  await writeFile(join(extraRoot, 'unexpected.ts'), 'export {};\n', 'utf8');
  await expectDrift(inventoryA, extraRoot, 'extra');

  const modifiedRoot = join(temporaryRoot, 'negative-modified');
  await cp(outputA, modifiedRoot, { recursive: true });
  const modifiedPath = join(modifiedRoot, ...firstFile.split('/'));
  const original = await readFile(modifiedPath, 'utf8');
  await writeFile(modifiedPath, `${original}\n`, 'utf8');
  await expectDrift(inventoryA, modifiedRoot, 'modified');

  const staleRoot = join(temporaryRoot, 'negative-stale');
  await cp(outputA, staleRoot, { recursive: true });
  await writeFile(join(staleRoot, 'stale.gen.ts'), 'export {};\n', 'utf8');
  await expectDrift(inventoryA, staleRoot, 'extra');

  console.log(
    JSON.stringify(
      {
        status: 'PASS',
        files: inventoryA,
        aggregateSha256: aggregateInventoryHash(inventoryA),
        openApiSha256: await openApiSha256(),
        determinism: 'A/B byte-identical',
        committed: 'byte-identical',
        driftNegatives: ['missing', 'extra', 'modified', 'stale'],
      },
      null,
      2,
    ),
  );
} catch (error) {
  console.log(
    JSON.stringify({
      status: 'FAIL',
      error:
        error instanceof Error
          ? error.message
          : 'Generated client check failed.',
    }),
  );
  process.exitCode = 1;
} finally {
  if (temporaryRoot) {
    await rm(temporaryRoot, { recursive: true, force: true });
  }
}

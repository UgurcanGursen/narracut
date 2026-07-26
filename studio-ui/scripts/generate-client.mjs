import {
  aggregateInventoryHash,
  committedOutputPath,
  generateClientTo,
  openApiSha256,
} from './client-generation.mjs';

try {
  const inventory = await generateClientTo(committedOutputPath);
  console.log(
    JSON.stringify(
      {
        status: 'PASS',
        files: inventory.length,
        aggregateSha256: aggregateInventoryHash(inventory),
        openApiSha256: await openApiSha256(),
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
          : 'Client generation failed.',
    }),
  );
  process.exit(1);
}

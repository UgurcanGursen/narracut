import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: '../shared-schemas/openapi/openapi.json',
  output: 'src/generated/kurgu-api',
  logs: {
    file: false,
    level: 'silent',
  },
  plugins: [
    '@hey-api/typescript',
    {
      name: '@hey-api/sdk',
      client: '@hey-api/client-fetch',
    },
    {
      name: '@hey-api/client-fetch',
      baseUrl: false,
      bundle: true,
    },
  ],
});

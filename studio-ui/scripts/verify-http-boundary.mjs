import { readFileSync, readdirSync } from 'node:fs';
import { dirname, extname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const projectRoot = dirname(scriptDirectory);
const sourceRoot = join(projectRoot, 'src');

function sourceFiles(root) {
  const files = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const absolute = join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...sourceFiles(absolute));
    } else if (['.ts', '.tsx'].includes(extname(entry.name))) {
      files.push(absolute);
    }
  }
  return files.sort();
}

function sourceName(file) {
  return relative(projectRoot, file).replaceAll('\\', '/');
}

function isProduction(file) {
  const name = sourceName(file);
  return (
    !name.includes('/generated/') &&
    !name.startsWith('src/test/') &&
    !name.endsWith('.test.ts') &&
    !name.endsWith('.test.tsx') &&
    !name.endsWith('.live.test.ts') &&
    !name.endsWith('.d.ts')
  );
}

function callName(expression) {
  if (ts.isIdentifier(expression)) {
    return expression.text;
  }
  if (
    ts.isPropertyAccessExpression(expression) &&
    ts.isIdentifier(expression.expression)
  ) {
    return `${expression.expression.text}.${expression.name.text}`;
  }
  return '';
}

export function verifyHttpBoundary() {
  const failures = [];
  const files = sourceFiles(sourceRoot);
  for (const file of files) {
    const name = sourceName(file);
    const text = readFileSync(file, 'utf8');
    const source = ts.createSourceFile(
      name,
      text,
      ts.ScriptTarget.Latest,
      true,
      name.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
    );
    const production = isProduction(file);
    const componentBoundary =
      name === 'src/App.tsx' || name.startsWith('src/components/');

    function fail(node, rule) {
      const location = source.getLineAndCharacterOfPosition(node.getStart());
      failures.push(`${name}:${location.line + 1}:${location.character + 1} ${rule}`);
    }

    function inspect(node) {
      if (
        ts.isImportDeclaration(node) &&
        ts.isStringLiteral(node.moduleSpecifier)
      ) {
        const specifier = node.moduleSpecifier.text;
        const generatedImport =
          specifier.includes('/generated/') ||
          specifier.startsWith('../generated') ||
          specifier.startsWith('./generated');
        const generatedAllowed =
          name === 'src/api/studioApi.ts' ||
          name === 'src/test/generatedClientContract.test.ts';
        if (generatedImport && !generatedAllowed) {
          fail(node, 'generated modules may only be imported by the facade or contract test');
        }
        if (
          componentBoundary &&
          (generatedImport ||
            specifier.startsWith('@hey-api/') ||
            specifier.includes('openapi.json'))
        ) {
          fail(node, 'React components must import only the handwritten API boundary');
        }
        if (
          production &&
          /^(node:)?(fs|path|child_process)(\/|$)/.test(specifier)
        ) {
          fail(node, 'production React source cannot import Node filesystem or process modules');
        }
        if (production && specifier === 'axios') {
          fail(node, 'Axios is forbidden in handwritten production source');
        }
        if (
          production &&
          (specifier.includes('kurgu_studio_api') ||
            specifier.includes('studio-api') ||
            specifier.endsWith('.py') ||
            specifier.includes('shared-schemas'))
        ) {
          fail(node, 'production React source cannot import backend or schema files');
        }
        if (production && specifier.split('/').includes('..')) {
          const normalized = specifier.replaceAll('\\', '/');
          if (normalized.startsWith('../../../')) {
            fail(node, 'production React source cannot traverse to the repository root');
          }
        }
      }

      if (production && ts.isCallExpression(node)) {
        const nameOfCall = callName(node.expression);
        if (['fetch', 'eval', 'process.exec'].includes(nameOfCall)) {
          fail(node, `${nameOfCall} is forbidden in handwritten production source`);
        }
      }

      if (production && ts.isNewExpression(node)) {
        const constructed = callName(node.expression);
        if (
          ['XMLHttpRequest', 'WebSocket', 'EventSource'].includes(constructed)
        ) {
          fail(node, `${constructed} is forbidden in handwritten production source`);
        }
      }

      if (
        production &&
        ts.isStringLiteralLike(node) &&
        (/file:\/\//i.test(node.text) ||
          /^[a-zA-Z]:[\\/]/.test(node.text) ||
          /\/api\/v1\/projects/.test(node.text))
      ) {
        fail(node, 'handwritten production source contains a forbidden path or endpoint literal');
      }

      if (production && node.kind === ts.SyntaxKind.AnyKeyword) {
        fail(node, 'handwritten production source cannot use any');
      }

      if (
        production &&
        ts.isIdentifier(node) &&
        node.text === 'process'
      ) {
        fail(node, 'handwritten production source cannot use process');
      }

      ts.forEachChild(node, inspect);
    }

    inspect(source);
  }

  if (failures.length) {
    throw new Error(failures.join('\n'));
  }
  return {
    status: 'PASS',
    files: files.length,
    productionFiles: files.filter(isProduction).length,
    generatedImporters: [
      'src/api/studioApi.ts',
      'src/test/generatedClientContract.test.ts',
    ],
  };
}

try {
  console.log(JSON.stringify(verifyHttpBoundary(), null, 2));
} catch (error) {
  console.log(
    JSON.stringify({
      status: 'FAIL',
      error:
        error instanceof Error
          ? error.message
          : 'HTTP boundary verification failed.',
    }),
  );
  process.exit(1);
}

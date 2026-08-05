import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import test from 'node:test';

const root = resolve(import.meta.dirname, '..');

test('Phase 5 templates use the pinned local readable font', () => {
  const templates = readFileSync(resolve(root, 'src', 'templates', 'index.tsx'), 'utf8');
  const composition = readFileSync(resolve(root, 'src', 'TemplateComposition.tsx'), 'utf8');
  const font = readFileSync(resolve(root, 'public', 'phase5-fonts', 'NotoSans-Variable.ttf'));
  assert.match(templates, /fontFamily:font/);
  assert.doesNotMatch(templates, /GlyphBars|const bars/);
  assert.match(composition, /NotoSans-Variable\.ttf/);
  assert.equal(font.subarray(0, 4).toString('ascii'), '\u0000\u0001\u0000\u0000');
});

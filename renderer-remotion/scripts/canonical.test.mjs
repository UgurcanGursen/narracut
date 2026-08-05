import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const canonical = (value) => Buffer.from(JSON.stringify(sort(value)));
const sort = (value) => Array.isArray(value) ? value.map(sort) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map((k) => [k,sort(value[k])])) : value;
test('canonical JSON has stable key order and SHA-256', () => {
  const a=canonical({z:1,a:{b:2,a:3}}); const b=canonical({a:{a:3,b:2},z:1});
  assert.deepEqual(a,b); assert.match(createHash('sha256').update(a).digest('hex'), /^[0-9a-f]{64}$/);
});

test('renderer does not select a host font and requires opaque source-ref bindings', () => {
  const source = readFileSync(resolve('src', 'sequence-preview.tsx'), 'utf8');
  const schema = readFileSync(resolve('src', 'schema.ts'), 'utf8');
  const runner = readFileSync(resolve('scripts', 'render-fixture.mjs'), 'utf8');
  assert.doesNotMatch(source, /fontFamily|Arial|sans-serif/);
  assert.match(source, /GlyphBars/);
  assert.match(schema, /asset_binding_source_ref/);
  assert.match(runner, /asset\.edl_source_ref !== binding\.edl_source_ref/);
  assert.match(runner, /CALLER_SOURCE/);
  assert.match(runner, /VISUAL_DIRECTIVE_INVALID/);
  assert.match(runner, /CHART_REVEAL/);
  assert.match(runner, /parseRenderProps/);
  assert.match(runner, /remotion-cli\.js/);
  assert.match(source, /zoom_start_millionths/);
  assert.match(source, /highlight_left_millionths/);
  assert.match(source, /chartRevealAtFrame/);
});

test('trusted fixture pixels, accepted V3 crop, and V4 reveal drive composition layers', () => {
  const source = readFileSync(resolve('src', 'sequence-preview.tsx'), 'utf8');
  const runner = readFileSync(resolve('scripts', 'render-fixture.mjs'), 'utf8');
  assert.match(source, /staticFile\(`phase4a-assets\/\$\{contentHash\.slice/);
  assert.match(source, /sourceCrop\(e\)/);
  assert.match(source, /crop_left_millionths/);
  assert.match(source, /crop_right_millionths/);
  assert.match(source, /trusted fixture \$\{binding\.fixture_asset_id\}/);
  assert.match(source, /clipPath:`inset\(0 \$\{100 - reveal \/ 10_000\}% 0 0\)`/);
  assert.match(runner, /copyFileSync\(asset\.candidate, target, constants\.COPYFILE_EXCL\)/);
  assert.match(runner, /asset\.media_type !== 'image\/svg\+xml'/);
  assert.doesNotMatch(runner, /process\.cwd\(\), 'public'/);
  assert.match(runner, /mkdtempSync\(resolve\(privateParent, 'phase4a-public-'\)\)/);
  assert.match(runner, /rmSync\(attemptPublicRoot, \{recursive: true, force: true/);
  assert.match(runner, /'--public-dir', attemptPublicRoot/);
  assert.ok(runner.indexOf("if (existsSync(out)) throw new Error('OUTPUT_TARGET_EXISTS')") < runner.indexOf("mkdirSync(attemptAssetRoot, {recursive: true})"));
  assert.match(runner, /directiveEvidenceFrames/);
  assert.match(runner, /SOURCE_ZOOM_HIGHLIGHT/);
  assert.match(runner, /event\.start_frame, event\.end_exclusive_frame - 1/);
});

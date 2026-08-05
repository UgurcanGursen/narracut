import assert from 'node:assert/strict';
import {existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import test from 'node:test';

test('Phase 7 registers an additive, closed visualization composition', () => {
  const index = readFileSync(resolve('src', 'index.tsx'), 'utf8');
  const source = readFileSync(resolve('src', 'visualization-replay.tsx'), 'utf8');
  assert.match(index, /id="visualization-replay-v1"/);
  assert.match(index, /VisualizationReplay/);
  assert.match(source, /parseVisualizationReplayProps/);
  assert.match(source, /VISUALIZATION_REPLAY_PROPS_INVALID/);
  assert.match(source, /source_captions/);
  assert.match(source, /chartForms/);
  assert.match(source, /FormGeometry/);
  assert.match(source, /polyline/);
  assert.match(source, /BigInt/);
  assert.doesNotMatch(source, /Number\(value\)/);
  assert.doesNotMatch(source, /sequence-preview-v1/);
});

test('isolated Phase 7 entry renders a data-dependent REPLAY frame', () => {
  const root=mkdtempSync(join(tmpdir(),'kurgu-phase7-')); const props=join(root,'props.json'), output=join(root,'frame.png');
  const input={schema_version:'VISUALIZATION-REPLAY-PROPS-V1',visualization_id:'viz_fixture',visualization_hash:`sha256:${'0'.repeat(64)}`,render_plan_id:'vizplan_fixture',render_plan_hash:`sha256:${'1'.repeat(64)}`,width:1280,height:720,duration_in_frames:3,forms:[{item_id:'chart_fixture',kind:'chart',form:'line'}],rows:[{element_id:'point_one',value:'10',label:'Q1'},{element_id:'point_two',value:'20',label:'Q2'}],source_captions:[{source_caption_id:'cap_fixture',text:'Example report - 2026-01-01'}],stages:[]};
  try { writeFileSync(props,JSON.stringify(input)); const result=spawnSync(process.execPath,['scripts/render-visualization-replay.mjs','--props',props,'--output',output,'--frame','1'],{cwd:process.cwd(),encoding:'utf8',timeout:120000,env:{...process.env,TZ:'UTC',LANG:'C',NODE_ENV:'production'}}); assert.equal(result.status,0,result.stderr); assert.ok(existsSync(output)); assert.deepEqual(readFileSync(output).subarray(0,8),Buffer.from([137,80,78,71,13,10,26,10])); } finally { rmSync(root,{recursive:true,force:true}); }
});

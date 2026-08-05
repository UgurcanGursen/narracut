import {existsSync, readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';

const value = (name) => { const index=process.argv.indexOf(name); return index < 0 ? null : process.argv[index+1] ?? null; };
const props=value('--props'), output=value('--output'), frame=value('--frame') ?? '0';
if (!props || !output || !/^[0-9]+$/.test(frame) || !existsSync(props) || existsSync(output)) throw new Error('VISUALIZATION_REPLAY_RUNNER_INVALID');
const input=JSON.parse(readFileSync(props,'utf8'));
if (input?.schema_version !== 'VISUALIZATION-REPLAY-PROPS-V1') throw new Error('VISUALIZATION_REPLAY_RUNNER_INVALID');
const cli=resolve('node_modules','@remotion','cli','remotion-cli.js');
const result=spawnSync(process.execPath,[cli,'still','src/visualization-entry.tsx','visualization-replay-v1',resolve(output),'--props',resolve(props),'--frame',frame,'--log','error'],{encoding:'utf8',timeout:120000,env:{...process.env,TZ:'UTC',LANG:'C',NODE_ENV:'production'}});
if (result.status !== 0) throw new Error('VISUALIZATION_REPLAY_RENDER_FAILED');

import {constants, copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync} from 'node:fs';
import {relative, resolve, sep} from 'node:path';
import {spawnSync} from 'node:child_process';
import {inflateSync} from 'node:zlib';
import {canonical, isHash, isUint, parseRenderProps, sha} from './render-props.mjs';

const fail = (code, detail = '') => { process.stderr.write(`${code}${detail ? `: ${detail}` : ''}\n`); process.exitCode = 2; };
const isRawDigest = (value) => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const rootsafe = (root, path) => { const r = resolve(root); const p = resolve(path); return p === r || p.startsWith(`${r}${sep}`); };
const args = process.argv.slice(2);
const option = (name) => { const at = args.indexOf(name); return at < 0 ? null : args[at + 1] ?? null; };
const propsPath = option('--props'); const outputRoot = option('--output'); const fixtureRoot = option('--fixture-root'); const workRoot = option('--work-root');
if (!propsPath || !outputRoot || !fixtureRoot || !workRoot) { fail('RECEIPT_INVALID', 'usage --props <file> --output <dir> --fixture-root <dir> --work-root <private-dir>'); }
else {
  try {
    const props = parseRenderProps({raw: readFileSync(resolve(propsPath)), packageLockPath: resolve(process.cwd(), 'package-lock.json')});
    if (props.video_tracks.length !== 7 || props.audio_tracks.length !== 5) throw new Error('NON_CANONICAL_PROPS');
    const manifestPath = resolve(fixtureRoot, 'fixture_asset_manifest.json');
    if (!rootsafe(fixtureRoot, manifestPath) || !existsSync(manifestPath)) throw new Error('ASSET_RESOLUTION_FAILED');
    const manifestBytes = readFileSync(manifestPath); const manifest = JSON.parse(manifestBytes.toString('utf8'));
    if (!Array.isArray(manifest.assets) || !Array.isArray(manifest.visual_directives) || !isHash(manifest.fixture_manifest_hash)) throw new Error('ASSET_RESOLUTION_FAILED');
    const manifestProjection = {...manifest}; delete manifestProjection.fixture_manifest_id; delete manifestProjection.fixture_manifest_hash;
    const manifestDigest = sha(canonical(manifestProjection));
    if (manifest.fixture_manifest_hash !== manifestDigest || typeof manifest.fixture_manifest_id !== 'string' || manifest.fixture_manifest_id.length === 0 || manifest.fixture_manifest_hash !== props.fixture_manifest_hash || manifest.fixture_manifest_id !== props.fixture_manifest_id) throw new Error('ASSET_RESOLUTION_FAILED');
    const assets = new Map(manifest.assets.map((asset) => [asset.fixture_asset_id, asset]));
    const eventById = new Map();
    for (const track of props.video_tracks) for (const event of track.events) {
      if (!event || typeof event.event_id !== 'string' || !event.payload || typeof event.payload !== 'object' || eventById.has(event.event_id)) throw new Error('NON_CANONICAL_PROPS');
      eventById.set(event.event_id, event);
    }
    const boundEvents = new Set();
    const trustedAssets = [];
    for (const binding of props.asset_bindings) {
      const asset = assets.get(binding.fixture_asset_id);
      const event = eventById.get(binding.event_id);
      if (!binding || typeof binding.event_id !== 'string' || typeof binding.edl_source_ref !== 'string' || boundEvents.has(binding.event_id) || !event || !event.payload.source || event.payload.source.source_ref !== binding.edl_source_ref || !asset || asset.edl_source_ref !== binding.edl_source_ref || asset.content_sha256 !== binding.content_sha256 || !isHash(binding.content_sha256) || !/^[^\\/]+(?:\/[^\\/]+)*$/.test(asset.relative_posix_path) || asset.relative_posix_path.includes('..')) throw new Error('ASSET_RESOLUTION_FAILED');
      boundEvents.add(binding.event_id);
      const candidate = resolve(fixtureRoot, ...asset.relative_posix_path.split('/'));
      if (!rootsafe(fixtureRoot, candidate) || !existsSync(candidate) || statSync(candidate).isSymbolicLink()) throw new Error('ASSET_RESOLUTION_FAILED');
      if (sha(readFileSync(candidate)) !== binding.content_sha256) throw new Error('ASSET_HASH_MISMATCH');
      if (asset.media_type !== 'image/svg+xml') throw new Error('ASSET_RESOLUTION_FAILED');
      // Do not materialize into the checked-in renderer public directory. The
      // input has now been authenticated, but writing it remains deferred until
      // the caller's output target has been proven absent below.
      trustedAssets.push({candidate, contentHash: binding.content_sha256});
    }
    for (const event of eventById.values()) if (event.payload.kind === 'CALLER_SOURCE' && !boundEvents.has(event.event_id)) throw new Error('ASSET_RESOLUTION_FAILED');
    const zoomKeys = ['schema_version','directive_id','directive_hash','event_id','event_hash','track','kind','zoom_start_millionths','zoom_end_millionths','highlight_left_millionths','highlight_top_millionths','highlight_right_millionths','highlight_bottom_millionths'];
    const revealKeys = ['schema_version','directive_id','directive_hash','event_id','event_hash','track','kind','reveal_start_millionths','reveal_end_millionths'];
    const directiveIds = new Set(); const directiveEvents = new Set(); let priorDirectiveId = '';
    for (const directive of manifest.visual_directives) {
      const isZoom = directive?.track === 'V3' && directive.kind === 'SOURCE_ZOOM_HIGHLIGHT';
      const isReveal = directive?.track === 'V4' && directive.kind === 'CHART_REVEAL';
      if (!directive || Object.keys(directive).join(',') !== (isZoom ? zoomKeys : revealKeys).join(',') || directive.schema_version !== 'FIXTURE-VISUAL-DIRECTIVE-V1' || typeof directive.directive_id !== 'string' || !isHash(directive.directive_hash) || typeof directive.event_id !== 'string' || !isRawDigest(directive.event_hash) || (!isZoom && !isReveal)) throw new Error('VISUAL_DIRECTIVE_INVALID');
      const numbers = isZoom ? ['zoom_start_millionths','zoom_end_millionths','highlight_left_millionths','highlight_top_millionths','highlight_right_millionths','highlight_bottom_millionths'] : ['reveal_start_millionths','reveal_end_millionths'];
      const geometryInvalid = isZoom && (directive.zoom_start_millionths < 1_000_000 || directive.zoom_start_millionths > directive.zoom_end_millionths || directive.zoom_end_millionths > 2_000_000 || directive.highlight_left_millionths >= directive.highlight_right_millionths || directive.highlight_right_millionths > 1_000_000 || directive.highlight_top_millionths >= directive.highlight_bottom_millionths || directive.highlight_bottom_millionths > 1_000_000);
      const revealInvalid = isReveal && (directive.reveal_start_millionths >= directive.reveal_end_millionths || directive.reveal_end_millionths > 1_000_000);
      if (numbers.some((key) => !isUint(directive[key])) || geometryInvalid || revealInvalid || directiveIds.has(directive.directive_id) || directiveEvents.has(directive.event_id) || directive.directive_id <= priorDirectiveId) throw new Error('VISUAL_DIRECTIVE_INVALID');
      const projection = {...directive}; delete projection.directive_id; delete projection.directive_hash; const digest = sha(canonical(projection));
      const event = eventById.get(directive.event_id);
      if (directive.directive_hash !== digest || directive.directive_id !== `vdir_${digest.slice(7,39)}` || !event || event.track !== directive.track || event.event_hash !== directive.event_hash || event.payload.kind !== 'CALLER_SOURCE' || !event.payload.source || !boundEvents.has(event.event_id)) throw new Error('VISUAL_DIRECTIVE_INVALID');
      directiveIds.add(directive.directive_id); directiveEvents.add(directive.event_id); priorDirectiveId = directive.directive_id;
    }
    if (!canonical(props.visual_directives).equals(canonical(manifest.visual_directives))) throw new Error('VISUAL_DIRECTIVE_INVALID');
    const out = resolve(outputRoot); if (existsSync(out)) throw new Error('OUTPUT_TARGET_EXISTS');
    const privateParent = resolve(workRoot);
    if (!existsSync(privateParent) || !statSync(privateParent).isDirectory()) throw new Error('RECEIPT_INVALID');
    // Browser-visible input is materialized only inside the Python-owned
    // temporary attempt.  It is removed even when Remotion exits non-zero;
    // the registered output root therefore retains just declared evidence.
    const attemptPublicRoot = mkdtempSync(resolve(privateParent, 'phase4a-public-'));
    try {
    const attemptAssetRoot = resolve(attemptPublicRoot, 'phase4a-assets');
    mkdirSync(attemptAssetRoot, {recursive: true});
    const materializedHashes = new Set();
    for (const asset of trustedAssets) {
      if (materializedHashes.has(asset.contentHash)) continue;
      const target = resolve(attemptAssetRoot, `${asset.contentHash.slice('sha256:'.length)}.svg`);
      if (!rootsafe(attemptAssetRoot, target)) throw new Error('ASSET_RESOLUTION_FAILED');
      copyFileSync(asset.candidate, target, constants.COPYFILE_EXCL);
      materializedHashes.add(asset.contentHash);
    }
    const framesDir = resolve(out, 'preview', 'frames'); mkdirSync(framesDir, {recursive: true});
    // The preview proves both endpoints of every allowlisted spatial motion.
    // Frame indices always come from the bound EDL event, never a directive
    // clock: V3 establishes zoom/highlight pixels and V4 chart reveal pixels.
    const directiveEvidenceFrames = manifest.visual_directives
      .filter((directive) => (directive.track === 'V3' && directive.kind === 'SOURCE_ZOOM_HIGHLIGHT') || (directive.track === 'V4' && directive.kind === 'CHART_REVEAL'))
      .flatMap((directive) => {
        const event = eventById.get(directive.event_id);
        return event ? [event.start_frame, event.end_exclusive_frame - 1] : [];
      });
    const frameSet = [...new Set([0, Math.floor(props.duration_frames / 2), props.duration_frames - 1, ...directiveEvidenceFrames])].sort((a,b) => a - b);
    for (const frame of frameSet) {
      const target = resolve(framesDir, `${frame}.png`);
      // Invoke the locked CLI JavaScript directly. Spawning the Windows .cmd shim
      // without a shell returns a false non-zero result; a shell would weaken path
      // isolation for caller-supplied CLI arguments.
      const cli = resolve(process.cwd(), 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
      if (!existsSync(cli)) throw new Error('REMOTION_UNAVAILABLE');
      const childEnv = {PATH: process.env.PATH ?? '', TZ: 'UTC', LANG: 'C', NODE_ENV: 'production'};
      if (process.platform === 'win32') { childEnv.SystemRoot = process.env.SystemRoot ?? ''; childEnv.COMSPEC = process.env.COMSPEC ?? ''; }
      const result = spawnSync(process.execPath, [cli, 'still', 'src/index.tsx', 'sequence-preview-v1', target, '--props', resolve(propsPath), '--public-dir', attemptPublicRoot, '--frame', String(frame), '--log', 'error'], {cwd: process.cwd(), encoding: 'utf8', timeout: 120000, env: childEnv});
      if (result.error?.code === 'ETIMEDOUT') throw new Error('RENDER_TIMEOUT');
      if (result.status !== 0) throw new Error('RENDER_EXIT_NONZERO');
    }
    const frames = frameSet.map((frame) => {
      const absolute = resolve(framesDir, `${frame}.png`); const bytes = readFileSync(absolute); const rgba = decodePngRgba(bytes);
      if (rgba.width !== 1280 || rgba.height !== 720) throw new Error('PREVIEW_FRAME_HASH_MISMATCH');
      return {frame_index: frame, relative_path: `preview/frames/${frame}.png`, png_sha256: sha(bytes), decoded_rgba_sha256: sha(rgba.bytes), width: rgba.width, height: rgba.height};
    });
    const result = {schema_version:'RENDER-MANIFEST-V1', manifest_id:null, manifest_hash:null, render_request_id:props.render_request_id, render_props_hash:props.render_props_hash, composition_id:props.composition_id, renderer_version:props.renderer_version, width:1280, height:720, fps_numerator:props.fps_numerator, fps_denominator:props.fps_denominator, duration_frames:props.duration_frames, pixel_format:'rgba', frames};
    const projection = {...result}; delete projection.manifest_id; delete projection.manifest_hash; const digest = sha(canonical(projection));
    result.manifest_hash = digest; result.manifest_id = `rman_${digest.slice('sha256:'.length, 'sha256:'.length + 32)}`;
    const manifestOut = resolve(out, 'preview', 'render-manifest.json'); writeFileSync(manifestOut, canonical(result));
    process.stdout.write(JSON.stringify({status:'SUCCEEDED', node_version:process.version, manifest_path:relative(out, manifestOut).replaceAll('\\','/'), manifest_id:result.manifest_id, manifest_hash:result.manifest_hash}) + '\n');
    } finally {
      rmSync(attemptPublicRoot, {recursive: true, force: true, maxRetries: 2, retryDelay: 50});
    }
  } catch (error) { fail(error instanceof Error ? error.message.split(':')[0] : 'RECEIPT_INVALID'); }
}

function decodePngRgba(bytes) {
  if (!bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error('PREVIEW_FRAME_HASH_MISMATCH');
  let offset = 8; let width = 0; let height = 0; let bitDepth = 0; let colorType = 0; const data = [];
  while (offset < bytes.length) { const length = bytes.readUInt32BE(offset); const type = bytes.subarray(offset + 4, offset + 8).toString('ascii'); const body = bytes.subarray(offset + 8, offset + 8 + length); offset += 12 + length; if (type === 'IHDR') { width=body.readUInt32BE(0); height=body.readUInt32BE(4); bitDepth=body[8]; colorType=body[9]; } else if (type === 'IDAT') data.push(body); else if (type === 'IEND') break; }
  if (!width || !height || bitDepth !== 8 || ![2,6].includes(colorType)) throw new Error('PREVIEW_FRAME_HASH_MISMATCH');
  const channels = colorType === 6 ? 4 : 3; const rowBytes = width * channels; const decoded = inflateSync(Buffer.concat(data)); if (decoded.length !== height * (rowBytes + 1)) throw new Error('PREVIEW_FRAME_HASH_MISMATCH');
  const scan = Buffer.alloc(height * rowBytes); let source = 0;
  for (let y=0;y<height;y++) { const filter=decoded[source++]; const row=y*rowBytes; for(let x=0;x<rowBytes;x++){ const a=x>=channels?scan[row+x-channels]:0; const b=y?scan[row-rowBytes+x]:0; const c=y&&x>=channels?scan[row-rowBytes+x-channels]:0; const value=decoded[source++]; scan[row+x]=(value + (filter===0?0:filter===1?a:filter===2?b:filter===3?Math.floor((a+b)/2):filter===4?paeth(a,b,c):(()=>{throw new Error('PREVIEW_FRAME_HASH_MISMATCH')})()))&255; } }
  const rgba=Buffer.alloc(width*height*4); for(let i=0,j=0;i<scan.length;i+=channels,j+=4){ rgba[j]=scan[i];rgba[j+1]=scan[i+1];rgba[j+2]=scan[i+2];rgba[j+3]=channels===4?scan[i+3]:255; } return {width,height,bytes:rgba};
}
function paeth(a,b,c) { const p=a+b-c, pa=Math.abs(p-a), pb=Math.abs(p-b), pc=Math.abs(p-c); return pa<=pb&&pa<=pc?a:pb<=pc?b:c; }

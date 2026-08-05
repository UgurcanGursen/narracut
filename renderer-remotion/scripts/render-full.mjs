import {existsSync, lstatSync, mkdirSync, readFileSync, statSync} from 'node:fs';
import {relative, resolve, sep} from 'node:path';
import {spawnSync} from 'node:child_process';
import {canonical, isHash, parseRenderProps, sha} from './render-props.mjs';

// This runner is intentionally only the visual producer.  Phase 4B Python
// orchestration owns toolchain preflight, PCM preparation, mux/encode, probe,
// receipt and publication.  In particular, this command must never invoke
// an audio muxer or create a final, audio-bearing deliverable.
const fail = (code, detail = '') => {
  process.stderr.write(`${code}${detail ? `: ${detail}` : ''}\n`);
  process.exitCode = 2;
};
const rootSafe = (root, candidate) => {
  const resolvedRoot = resolve(root);
  const resolvedCandidate = resolve(candidate);
  return resolvedCandidate === resolvedRoot || resolvedCandidate.startsWith(`${resolvedRoot}${sep}`);
};
const argument = (args, name) => {
  const index = args.indexOf(name);
  return index < 0 ? null : args[index + 1] ?? null;
};
const regularDirectory = (path) => existsSync(path) && !lstatSync(path).isSymbolicLink() && statSync(path).isDirectory();
const regularFile = (path) => existsSync(path) && !lstatSync(path).isSymbolicLink() && statSync(path).isFile();

const args = process.argv.slice(2);
const propsPath = argument(args, '--props');
const outputPath = argument(args, '--output');
const publicDir = argument(args, '--public-dir');
if (!propsPath || !outputPath || !publicDir || args.length !== 6) {
  fail('RECEIPT_INVALID', 'usage --props <canonical-file> --output <new-video.mp4> --public-dir <attempt-local-public-dir>');
} else {
  try {
    const propsFile = resolve(propsPath);
    const outputFile = resolve(outputPath);
    const attemptPublicRoot = resolve(publicDir);
    if (!regularFile(propsFile) || !regularDirectory(attemptPublicRoot) || existsSync(outputFile)) {
      throw new Error('RECEIPT_INVALID');
    }
    const props = parseRenderProps({raw: readFileSync(propsFile), packageLockPath: resolve(process.cwd(), 'package-lock.json')});
    if (props.composition_id !== 'sequence-preview-v1' || props.width !== 1280 || props.height !== 720 || props.pixel_format !== 'rgba') {
      throw new Error('NON_CANONICAL_PROPS');
    }

    // The 4A bridge authenticated each binding against the fixture manifest.
    // This producer rechecks the attempt-local copies, so the browser can only
    // read exact content-addressed assets selected by that bridge.
    const seenEventIds = new Set();
    const seenHashes = new Set();
    for (const binding of props.asset_bindings) {
      if (!binding || typeof binding.event_id !== 'string' || seenEventIds.has(binding.event_id) || !isHash(binding.content_sha256)) {
        throw new Error('ASSET_RESOLUTION_FAILED');
      }
      seenEventIds.add(binding.event_id);
      const filename = `${binding.content_sha256.slice('sha256:'.length)}.svg`;
      const asset = resolve(attemptPublicRoot, 'phase4a-assets', filename);
      if (!rootSafe(attemptPublicRoot, asset) || !regularFile(asset) || sha(readFileSync(asset)) !== binding.content_sha256) {
        throw new Error('ASSET_HASH_MISMATCH');
      }
      seenHashes.add(binding.content_sha256);
    }
    if (seenHashes.size === 0) throw new Error('ASSET_RESOLUTION_FAILED');

    const parent = resolve(outputFile, '..');
    if (!rootSafe(parent, outputFile)) throw new Error('RECEIPT_INVALID');
    mkdirSync(parent, {recursive: true});
    const cli = resolve(process.cwd(), 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
    if (!regularFile(cli)) throw new Error('REMOTION_UNAVAILABLE');
    const childEnv = {PATH: process.env.PATH ?? '', TZ: 'UTC', LANG: 'C', NODE_ENV: 'production'};
    if (process.platform === 'win32') {
      childEnv.SystemRoot = process.env.SystemRoot ?? '';
      childEnv.COMSPEC = process.env.COMSPEC ?? '';
    }
    const result = spawnSync(process.execPath, [
      cli, 'render', 'src/index.tsx', props.composition_id, outputFile,
      '--props', propsFile, '--public-dir', attemptPublicRoot,
      '--codec', 'h264', '--pixel-format', 'yuv420p', '--log', 'error',
    ], {cwd: process.cwd(), encoding: 'utf8', timeout: 300000, env: childEnv});
    if (result.error?.code === 'ETIMEDOUT') throw new Error('RENDER_TIMEOUT');
    if (result.status !== 0 || !regularFile(outputFile) || statSync(outputFile).size === 0) throw new Error('REMOTION_FULL_RENDER_FAILED');
    const outputBytes = readFileSync(outputFile);
    const resultManifest = {
      schema_version: 'REMOTION-FULL-VIDEO-V1',
      render_request_id: props.render_request_id,
      render_props_hash: props.render_props_hash,
      composition_id: props.composition_id,
      width: props.width,
      height: props.height,
      fps_numerator: props.fps_numerator,
      fps_denominator: props.fps_denominator,
      duration_frames: props.duration_frames,
      video_relative_path: relative(parent, outputFile).replaceAll('\\', '/'),
      video_sha256: sha(outputBytes),
      video_byte_length: outputBytes.length,
    };
    // stdout is a bounded handoff to Python, not a receipt or artifact record.
    process.stdout.write(canonical(resultManifest).toString('utf8') + '\n');
  } catch (error) {
    fail(error instanceof Error ? error.message.split(':')[0] : 'RECEIPT_INVALID');
  }
}

import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';

export const sha = (value) => `sha256:${createHash('sha256').update(value).digest('hex')}`;
export const plain = (value) => {
  if (Array.isArray(value)) return value.map(plain);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, plain(value[key])]));
  if (typeof value === 'number' && (!Number.isFinite(value) || !Number.isInteger(value))) throw new Error('NON_CANONICAL_PROPS');
  if (typeof value === 'string' && value.normalize('NFC') !== value) throw new Error('NON_CANONICAL_PROPS');
  return value;
};
export const canonical = (value) => Buffer.from(JSON.stringify(plain(value)), 'utf8');
export const isHash = (value) => typeof value === 'string' && /^sha256:[0-9a-f]{64}$/.test(value);
export const isUint = (value) => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;

const ROOT_KEYS = ['schema_version','hash_scope_version','render_props_id','render_props_hash','render_request_id','mode','renderer_version','project_id','document_id','narration_revision_id','sequence_id','video_edl_id','video_edl_hash','audio_edl_id','audio_edl_hash','word_to_frame_id','word_to_frame_hash','fps_numerator','fps_denominator','duration_frames','duration_samples','width','height','pixel_format','composition_id','design_system_version','fixture_manifest_id','fixture_manifest_hash','video_tracks','audio_tracks','audio_boundary_decisions','asset_bindings','visual_directives'];
const requestProjection = (props) => ({schema_version:'RENDER-REQUEST-ID-V1', render_props_hash:props.render_props_hash, composition_id:props.composition_id, renderer_version:props.renderer_version, fixture_manifest_hash:props.fixture_manifest_hash});

/** Shared closed ingress for the CLI runner. The React bundle rechecks its structural subset. */
export const parseRenderProps = ({raw, packageLockPath}) => {
  if (!Buffer.isBuffer(raw) || raw.subarray(0, 3).equals(Buffer.from([0xef, 0xbb, 0xbf]))) throw new Error('NON_CANONICAL_PROPS');
  const props = JSON.parse(raw.toString('utf8'));
  if (!raw.equals(canonical(props)) || !props || typeof props !== 'object' || Array.isArray(props) || Object.keys(props).sort().join(',') !== ROOT_KEYS.slice().sort().join(',')) throw new Error('NON_CANONICAL_PROPS');
  if (props.schema_version !== 'RENDER-PROPS-V1' || props.hash_scope_version !== 'RENDER-PROPS-HASH-V1' || props.mode !== 'PREVIEW' || props.composition_id !== 'sequence-preview-v1' || props.width !== 1280 || props.height !== 720 || props.pixel_format !== 'rgba') throw new Error('NON_CANONICAL_PROPS');
  for (const key of ['render_props_id','render_props_hash','render_request_id','renderer_version','project_id','document_id','narration_revision_id','sequence_id','video_edl_id','video_edl_hash','audio_edl_id','audio_edl_hash','word_to_frame_id','word_to_frame_hash','design_system_version','fixture_manifest_id','fixture_manifest_hash']) if (typeof props[key] !== 'string' || props[key].length === 0) throw new Error('NON_CANONICAL_PROPS');
  // Phase 3 EDL and WordToFrame hashes are accepted upstream bare digests;
  // only Phase 4-owned props/fixture identities carry the sha256: envelope.
  if (!isHash(props.render_props_hash) || !isHash(props.fixture_manifest_hash) || !['video_edl_hash','audio_edl_hash','word_to_frame_hash'].every((key) => /^[0-9a-f]{64}$/.test(props[key])) || !['fps_numerator','fps_denominator','duration_frames','duration_samples'].every((key) => isUint(props[key]) && props[key] > 0)) throw new Error('NON_CANONICAL_PROPS');
  const lockDigest = createHash('sha256').update(readFileSync(packageLockPath)).digest('hex');
  if (props.renderer_version !== `RRV1|bridge=0.1.0|package_lock_sha256=${lockDigest}`) throw new Error('NON_CANONICAL_PROPS');
  const identity = {...props}; delete identity.render_props_id; delete identity.render_props_hash; delete identity.render_request_id;
  const expectedHash = sha(canonical(identity));
  if (props.render_props_hash !== expectedHash || props.render_props_id !== `rprops_${expectedHash.slice(7,39)}` || props.render_request_id !== `rrq_${createHash('sha256').update(canonical(requestProjection(props))).digest('hex').slice(0,32)}`) throw new Error('NON_CANONICAL_PROPS');
  if (!Array.isArray(props.video_tracks) || !Array.isArray(props.audio_tracks) || !Array.isArray(props.audio_boundary_decisions) || !Array.isArray(props.asset_bindings) || !Array.isArray(props.visual_directives)) throw new Error('NON_CANONICAL_PROPS');
  return props;
};

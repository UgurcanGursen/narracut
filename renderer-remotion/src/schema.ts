import type {RenderProps, Json, VisualDirective} from './types';

const tracks = ['V1','V2','V3','V4','V5','V6','V7'];
const audioTracks = ['A1','A2','A3','A4','A5'];
const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const isUint = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const nonEmpty = (v: unknown): v is string => typeof v === 'string' && v.length > 0;
const sha = (v: unknown) => typeof v === 'string' && /^sha256:[0-9a-f]{64}$/.test(v);

/** Deliberately strict ingress validator; the Python bridge remains identity authority. */
export const parseRenderProps = (input: unknown): RenderProps => {
  if (!isObject(input)) throw new Error('NON_CANONICAL_PROPS: root');
  const p = input as Record<string, unknown>;
  for (const k of ['schema_version','hash_scope_version','render_props_id','render_props_hash','render_request_id','renderer_version','project_id','document_id','narration_revision_id','sequence_id','video_edl_id','video_edl_hash','audio_edl_id','audio_edl_hash','word_to_frame_id','word_to_frame_hash','design_system_version','fixture_manifest_id','fixture_manifest_hash']) if (!nonEmpty(p[k])) throw new Error(`NON_CANONICAL_PROPS: ${k}`);
  if (p.schema_version !== 'RENDER-PROPS-V1' || p.mode !== 'PREVIEW' || p.pixel_format !== 'rgba' || p.composition_id !== 'sequence-preview-v1') throw new Error('NON_CANONICAL_PROPS: fixed literals');
  if (!sha(p.render_props_hash) || !sha(p.fixture_manifest_hash) || !['video_edl_hash','audio_edl_hash','word_to_frame_hash'].every((key) => typeof p[key] === 'string' && /^[0-9a-f]{64}$/.test(p[key]))) throw new Error('NON_CANONICAL_PROPS: digest');
  for (const k of ['fps_numerator','fps_denominator','duration_frames','duration_samples','width','height']) if (!isUint(p[k]) || p[k] === 0) throw new Error(`NON_CANONICAL_PROPS: ${k}`);
  if (p.width !== 1280 || p.height !== 720) throw new Error('NON_CANONICAL_PROPS: dimensions');
  if (!Array.isArray(p.video_tracks) || p.video_tracks.length !== 7 || !p.video_tracks.every((t, i) => isObject(t) && t.track === tracks[i] && isUint(t.priority) && Array.isArray(t.events))) throw new Error('NON_CANONICAL_PROPS: video_tracks');
  if (!Array.isArray(p.audio_tracks) || p.audio_tracks.length !== 5 || !p.audio_tracks.every((t, i) => isObject(t) && t.track === audioTracks[i] && isUint(t.priority) && Array.isArray(t.events))) throw new Error('NON_CANONICAL_PROPS: audio_tracks');
  if (!Array.isArray(p.audio_boundary_decisions) || !Array.isArray(p.asset_bindings) || !Array.isArray(p.visual_directives)) throw new Error('NON_CANONICAL_PROPS: arrays');
  const eventById = new Map<string, Record<string, unknown>>();
  for (const track of p.video_tracks) for (const event of (track as {events: unknown[]}).events) {
    if (!isObject(event) || !nonEmpty(event.event_id) || !isObject(event.payload)) throw new Error('NON_CANONICAL_PROPS: video_event');
    if (eventById.has(event.event_id)) throw new Error('NON_CANONICAL_PROPS: duplicate_event_id');
    eventById.set(event.event_id, event);
  }
  const boundEventIds = new Set<string>();
  for (const b of p.asset_bindings) {
    if (!isObject(b) || !nonEmpty(b.event_id) || !nonEmpty(b.fixture_asset_id) || !nonEmpty(b.edl_source_ref) || !sha(b.content_sha256) || !nonEmpty(b.media_type) || !isUint(b.width) || !isUint(b.height)) throw new Error('NON_CANONICAL_PROPS: asset_binding');
    if (boundEventIds.has(b.event_id)) throw new Error('NON_CANONICAL_PROPS: duplicate_asset_binding');
    boundEventIds.add(b.event_id);
    const event = eventById.get(b.event_id); const payload = event?.payload as Record<string, unknown> | undefined; const source = payload?.source;
    if (!isObject(source) || source.source_ref !== b.edl_source_ref) throw new Error('NON_CANONICAL_PROPS: asset_binding_source_ref');
  }
  const directives = p.visual_directives as unknown[];
  const directiveIds = new Set<string>(); const directiveEvents = new Set<string>(); let priorDirectiveId = '';
  for (const directive of directives) {
    if (!isObject(directive) || directive.schema_version !== 'FIXTURE-VISUAL-DIRECTIVE-V1' || !nonEmpty(directive.directive_id) || !sha(directive.directive_hash) || !nonEmpty(directive.event_id) || typeof directive.event_hash !== 'string' || !/^[0-9a-f]{64}$/.test(directive.event_hash)) throw new Error('VISUAL_DIRECTIVE_INVALID');
    const zoom = directive.track === 'V3' && directive.kind === 'SOURCE_ZOOM_HIGHLIGHT';
    const reveal = directive.track === 'V4' && directive.kind === 'CHART_REVEAL';
    if (!zoom && !reveal) throw new Error('VISUAL_DIRECTIVE_INVALID');
    const values = zoom ? ['zoom_start_millionths','zoom_end_millionths','highlight_left_millionths','highlight_top_millionths','highlight_right_millionths','highlight_bottom_millionths'] : ['reveal_start_millionths','reveal_end_millionths'];
    if (values.some((key) => !isUint(directive[key]))) throw new Error('VISUAL_DIRECTIVE_INVALID');
    const value = directive as unknown as VisualDirective;
    const rangeInvalid = value.kind === 'SOURCE_ZOOM_HIGHLIGHT'
      ? (value.zoom_start_millionths < 1_000_000 || value.zoom_start_millionths > value.zoom_end_millionths || value.zoom_end_millionths > 2_000_000 || value.highlight_left_millionths >= value.highlight_right_millionths || value.highlight_right_millionths > 1_000_000 || value.highlight_top_millionths >= value.highlight_bottom_millionths || value.highlight_bottom_millionths > 1_000_000)
      : (value.reveal_start_millionths >= value.reveal_end_millionths || value.reveal_end_millionths > 1_000_000);
    if (rangeInvalid || directiveIds.has(value.directive_id) || directiveEvents.has(value.event_id) || value.directive_id <= priorDirectiveId) throw new Error('VISUAL_DIRECTIVE_INVALID');
    const event = eventById.get(value.event_id); const payload = event?.payload as Record<string, unknown> | undefined;
    if (!event || event.track !== value.track || event.event_hash !== value.event_hash || !isObject(payload?.source)) throw new Error('VISUAL_DIRECTIVE_INVALID');
    directiveIds.add(value.directive_id); directiveEvents.add(value.event_id); priorDirectiveId = value.directive_id;
  }
  return p as unknown as RenderProps;
};

export const assertNoNonFinite = (value: Json): void => {
  if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('NON_CANONICAL_PROPS: non-finite');
  if (Array.isArray(value)) value.forEach(assertNoNonFinite);
  if (isObject(value)) Object.values(value as Record<string, Json>).forEach(assertNoNonFinite);
};

export type Json = null | boolean | number | string | Json[] | {[key: string]: Json};

export interface RenderProps {
  schema_version: 'RENDER-PROPS-V1'; hash_scope_version: string;
  render_props_id: string; render_props_hash: string; render_request_id: string;
  mode: 'PREVIEW'; renderer_version: string;
  project_id: string; document_id: string; narration_revision_id: string; sequence_id: string;
  video_edl_id: string; video_edl_hash: string; audio_edl_id: string; audio_edl_hash: string;
  word_to_frame_id: string; word_to_frame_hash: string;
  fps_numerator: number; fps_denominator: number; duration_frames: number; duration_samples: number;
  width: 1280; height: 720; pixel_format: 'rgba'; composition_id: 'sequence-preview-v1';
  design_system_version: string; fixture_manifest_id: string; fixture_manifest_hash: string;
  video_tracks: VideoTrack[]; audio_tracks: AudioTrack[]; audio_boundary_decisions: Json[]; asset_bindings: AssetBinding[]; visual_directives: VisualDirective[];
}
export interface VideoEvent { event_id: string; track: string; ordinal: number; start_frame: number; end_exclusive_frame: number; editorial_role: string; payload: Record<string, Json>; [key: string]: Json; }
export interface VideoTrack {track: string; kind: string; priority: number; events: VideoEvent[];}
export interface AudioTrack {track: string; priority: number; events: Json[];}
/** `source_ref` is the opaque EDL reference, never a path or provider locator. */
export interface AssetBinding {event_id: string; edl_source_ref: string; fixture_asset_id: string; content_sha256: string; media_type: string; width: number; height: number;}
export interface SourceZoomHighlightDirective {
  schema_version: 'FIXTURE-VISUAL-DIRECTIVE-V1'; directive_id: string; directive_hash: string;
  event_id: string; event_hash: string; track: 'V3'; kind: 'SOURCE_ZOOM_HIGHLIGHT';
  zoom_start_millionths: number; zoom_end_millionths: number;
  highlight_left_millionths: number; highlight_top_millionths: number;
  highlight_right_millionths: number; highlight_bottom_millionths: number;
}
export interface ChartRevealDirective {
  schema_version: 'FIXTURE-VISUAL-DIRECTIVE-V1'; directive_id: string; directive_hash: string;
  event_id: string; event_hash: string; track: 'V4'; kind: 'CHART_REVEAL';
  reveal_start_millionths: number; reveal_end_millionths: number;
}
export type VisualDirective = SourceZoomHighlightDirective | ChartRevealDirective;

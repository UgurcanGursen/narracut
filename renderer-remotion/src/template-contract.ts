import type {RenderProps} from './types';

export const TEMPLATE_IDS = [
  'article_focus_scan', 'caption_phrase', 'chapter_title', 'cold_open_source_montage',
  'expert_quote_card', 'final_thesis_card', 'headline_to_paragraph_zoom', 'highlight_wipe',
  'kinetic_keyword', 'metric_comparison', 'metric_reveal', 'news_clip_context',
  'process_diagram', 'split_screen_comparison', 'timeline_progression',
] as const;
export type TemplateId = typeof TEMPLATE_IDS[number];
export type TemplateKind = 'SOURCE' | 'TEXT' | 'METRIC' | 'DIAGRAM' | 'COMPARISON' | 'KINETIC';
export type PayloadKind = 'SOURCE_TEXT' | 'TITLE_BODY' | 'QUOTE' | 'METRIC_SINGLE' | 'METRIC_PAIR' | 'DIAGRAM' | 'TIMELINE' | 'COMPARISON' | 'KINETIC';
export const SAFE_AREA_POLICY = 'SAFE-AREA-V1' as const;
export const SAFE_AREA_MILLIONTHS = Object.freeze({content: [64_000, 56_000, 936_000, 746_000], subtitle: [64_000, 772_000, 936_000, 936_000]} as const);
export type RectMillionths = {left_millionths: number; top_millionths: number; right_millionths: number; bottom_millionths: number};

export type SourceTextPayload = {headline: string; body: string};
export type TitleBodyPayload = {title: string; body: string};
export type QuotePayload = {quote: string; attribution: string};
export type MetricSinglePayload = {label: string; value: string; qualifier: string};
export type MetricPairPayload = {left_label: string; left_value: string; right_label: string; right_value: string; qualifier: string};
export type DiagramPayload = {nodes: {node_id: string; label: string}[]; edges: {from_node_id: string; to_node_id: string}[]};
export type TimelinePayload = {points: {point_id: string; label: string; ordinal: number}[]};
export type ComparisonPayload = {left_label: string; right_label: string; conclusion: string};
export type KineticPayload = {display_text: string};
export type TemplatePayload = SourceTextPayload | TitleBodyPayload | QuotePayload | MetricSinglePayload | MetricPairPayload | DiagramPayload | TimelinePayload | ComparisonPayload | KineticPayload;

export type WordBindingV1 = {narration_revision_id: string; word_to_frame_id: string; word_to_frame_hash: string; start_word_id: string; end_word_id: string; start_frame: number; end_exclusive_frame: number};
export type TemplateStylePresetV1 = {preset_id: string; color_theme_id: string; typography_id: string; font_asset_hash: string; tone_id: string; preset_hash: string; policy_snapshot_id: string | null; policy_snapshot_hash: string | null};
export type TemplateDefinition = Readonly<{template_id: TemplateId; template_version: '1.0.0'; kind: TemplateKind; supported_editorial_roles: readonly string[]; requires_source_asset: boolean; supports_target_region: boolean; supports_caption: boolean; supports_source_label: boolean; supports_word_binding: boolean; safe_area_policy: typeof SAFE_AREA_POLICY; payload_kind: PayloadKind}>;
export type TemplateInvocationV1 = Readonly<{template_id: TemplateId; template_version: '1.0.0'; editorial_role: string; start_frame: number; end_exclusive_frame: number; layout: RectMillionths; source_event_id: string | null; target_region: RectMillionths | null; entry_animation: string; exit_animation: string; camera_motion: string; caption: string | null; source_label: string | null; style_preset_id: string; payload: TemplatePayload; word_binding: WordBindingV1 | null; safe_area_policy: typeof SAFE_AREA_POLICY}>;
export type TemplateRenderPlanV1 = Readonly<{schema_version: 'TEMPLATE-RENDER-PLAN-V1'; template_plan_id: string; template_plan_hash: string; render_request_id: string; render_props_hash: string; word_to_frame_id: string; word_to_frame_hash: string; style_preset: TemplateStylePresetV1; invocations: readonly TemplateInvocationV1[]}>;
export type WordFrame = Readonly<{start_word_id: string; end_word_id: string; start_frame: number; end_exclusive_frame: number; start_word_ordinal: number; end_exclusive_word_ordinal: number}>;
export type WordToFrameArtifactV1 = Readonly<{schema_version: 'WORD-TO-FRAME-V1'; word_to_frame_id: string; word_to_frame_hash: string; narration_revision_id: string; narration_revision_hash: string; frame_rate: {numerator: number; denominator: number}; word_frames: readonly WordFrame[]; [key: string]: unknown}>;
export type TemplateRenderInputV1 = Readonly<{schema_version: 'TEMPLATE-RENDER-INPUT-V1'; template_input_id: string; template_input_hash: string; render_props: RenderProps; template_render_plan: TemplateRenderPlanV1; word_to_frame_artifact: WordToFrameArtifactV1}>;

const definition = (template_id: TemplateId, kind: TemplateKind, roles: readonly string[], payload_kind: PayloadKind, flags: readonly [boolean, boolean, boolean, boolean, boolean]): TemplateDefinition => Object.freeze({template_id, template_version:'1.0.0', kind, supported_editorial_roles:Object.freeze([...roles]), requires_source_asset:flags[0], supports_target_region:flags[1], supports_caption:flags[2], supports_source_label:flags[3], supports_word_binding:flags[4], safe_area_policy:SAFE_AREA_POLICY, payload_kind});
export const TEMPLATE_DEFINITIONS: readonly TemplateDefinition[] = Object.freeze([
  definition('article_focus_scan','SOURCE',['prove_claim','context'],'SOURCE_TEXT',[true,true,false,true,false]),
  definition('caption_phrase','KINETIC',['caption'],'KINETIC',[false,false,true,false,true]),
  definition('chapter_title','TEXT',['chapter','introduce'],'TITLE_BODY',[false,false,true,false,false]),
  definition('cold_open_source_montage','SOURCE',['introduce','context'],'SOURCE_TEXT',[true,false,false,true,false]),
  definition('expert_quote_card','TEXT',['quote','context'],'QUOTE',[false,false,true,true,false]),
  definition('final_thesis_card','TEXT',['conclude','emphasize'],'TITLE_BODY',[false,false,true,false,false]),
  definition('headline_to_paragraph_zoom','SOURCE',['prove_claim','context'],'SOURCE_TEXT',[true,true,false,true,false]),
  definition('highlight_wipe','SOURCE',['prove_claim','emphasize'],'SOURCE_TEXT',[true,true,false,true,false]),
  definition('kinetic_keyword','KINETIC',['emphasize'],'KINETIC',[false,false,true,false,true]),
  definition('metric_comparison','METRIC',['compare','quantify'],'METRIC_PAIR',[false,false,true,true,false]),
  definition('metric_reveal','METRIC',['quantify','prove_claim'],'METRIC_SINGLE',[false,false,true,true,false]),
  definition('news_clip_context','SOURCE',['context','prove_claim'],'SOURCE_TEXT',[true,false,true,true,false]),
  definition('process_diagram','DIAGRAM',['explain_mechanism','context'],'DIAGRAM',[false,false,true,false,false]),
  definition('split_screen_comparison','COMPARISON',['compare','context'],'COMPARISON',[true,false,true,true,false]),
  definition('timeline_progression','DIAGRAM',['chronology','context'],'TIMELINE',[false,false,true,false,false]),
]);
export const templateDefinition = (id: TemplateId): TemplateDefinition => {
  const definition = TEMPLATE_DEFINITIONS.find((item) => item.template_id === id);
  if (!definition) throw new Error('TEMPLATE_UNKNOWN');
  return definition;
};

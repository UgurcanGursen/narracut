import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
const id = (value: unknown): value is string => typeof value === 'string' && /^[a-z][a-z0-9_]{0,127}$/.test(value);
const hash = (value: unknown): value is string => typeof value === 'string' && /^sha256:[0-9a-f]{64}$/.test(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.trim() === value && value.length > 0;
const positiveInteger = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 1;
const nonNegativeInteger = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const chartForms = new Set(['line','bar','area','stacked','comparison','waterfall','timeline']);
const topologyForms = new Set(['timeline','relationship_graph','evidence_chain','map']);
const formAllowed = (kind: string, form: string): boolean => (kind === 'chart' && chartForms.has(form)) || (kind === 'metric' && form === 'metric') || (topologyForms.has(kind) && form === kind);

export type VisualizationReplayRowV1 = Readonly<{element_id: string; value: string; label: string}>;
export type VisualizationReplayCaptionV1 = Readonly<{source_caption_id: string; text: string}>;
export type VisualizationReplayFormV1 = Readonly<{item_id: string; kind: string; form: string}>;
export type VisualizationReplayStageV1 = Readonly<{stage_id: string; target_ids: readonly string[]; start_frame: number; end_exclusive_frame: number}>;
export type VisualizationReplayPropsV1 = Readonly<{
  schema_version: 'VISUALIZATION-REPLAY-PROPS-V1'; visualization_id: string; visualization_hash: string;
  render_plan_id: string; render_plan_hash: string; width: number; height: number; duration_in_frames: number;
  forms: readonly VisualizationReplayFormV1[]; rows: readonly VisualizationReplayRowV1[]; source_captions: readonly VisualizationReplayCaptionV1[]; stages: readonly VisualizationReplayStageV1[];
}>;

/** Closed Node ingress for Python-verified Phase 7 REPLAY metadata projections. */
export const parseVisualizationReplayProps = (raw: unknown): VisualizationReplayPropsV1 => {
  if (!object(raw) || Object.keys(raw).length !== 12 || raw.schema_version !== 'VISUALIZATION-REPLAY-PROPS-V1' || !id(raw.visualization_id) || !hash(raw.visualization_hash) || !id(raw.render_plan_id) || !hash(raw.render_plan_hash) || !positiveInteger(raw.width) || !positiveInteger(raw.height) || !positiveInteger(raw.duration_in_frames) || !Array.isArray(raw.forms) || !Array.isArray(raw.rows) || !Array.isArray(raw.source_captions) || !Array.isArray(raw.stages)) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID');
  const seen = new Set<string>();
  for (const form of raw.forms) { if (!object(form) || Object.keys(form).length !== 3 || !id(form.item_id) || !text(form.kind) || !text(form.form) || !formAllowed(form.kind, form.form) || seen.has(form.item_id)) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID'); seen.add(form.item_id); }
  for (const row of raw.rows) { if (!object(row) || Object.keys(row).length !== 3 || !id(row.element_id) || !text(row.value) || !text(row.label) || seen.has(row.element_id)) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID'); seen.add(row.element_id); }
  for (const caption of raw.source_captions) { if (!object(caption) || Object.keys(caption).length !== 2 || !id(caption.source_caption_id) || !text(caption.text) || seen.has(caption.source_caption_id)) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID'); seen.add(caption.source_caption_id); }
  const stageIds = new Set<string>(); const stages: {target_ids: string[]; start_frame: number; end_exclusive_frame: number}[] = [];
  for (const stage of raw.stages) {
    if (!object(stage) || Object.keys(stage).length !== 4 || !id(stage.stage_id) || !Array.isArray(stage.target_ids) || !nonNegativeInteger(stage.start_frame) || !positiveInteger(stage.end_exclusive_frame)) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID');
    const targetIds = stage.target_ids as unknown[]; const startFrame = stage.start_frame; const endFrame = stage.end_exclusive_frame;
    if (targetIds.length === 0 || !targetIds.every(id) || new Set(targetIds).size !== targetIds.length || startFrame >= endFrame || endFrame > raw.duration_in_frames || stageIds.has(stage.stage_id) || stages.some((prior) => targetIds.some((target: string) => prior.target_ids.includes(target)) && Math.max(startFrame, prior.start_frame) < Math.min(endFrame, prior.end_exclusive_frame))) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID');
    stages.push({target_ids:targetIds as string[], start_frame:startFrame, end_exclusive_frame:endFrame}); stageIds.add(stage.stage_id);
  }
  return raw as unknown as VisualizationReplayPropsV1;
};

const decimalCoordinate = (value: string): {coefficient: bigint; scale: number} => {
  const match = /^(-?)(0|[1-9][0-9]*)(?:\.([0-9]{1,12}))?$/.exec(value);
  if (!match) throw new Error('VISUALIZATION_REPLAY_PROPS_INVALID');
  return {coefficient: BigInt(`${match[1]}${match[2]}${match[3] ?? ''}`), scale:(match[3] ?? '').length};
};
const FormGeometry: React.FC<{form: string; rows: readonly VisualizationReplayRowV1[]}> = ({form, rows}) => {
  const values = rows.filter((row) => /^-?(0|[1-9][0-9]*)(?:\.[0-9]{1,12})?$/.test(row.value)).map((row) => decimalCoordinate(row.value)); if (values.length === 0) values.push({coefficient:1n, scale:0}); const scale = Math.max(...values.map((value) => value.scale)); const normalized = values.map((value) => value.coefficient * 10n ** BigInt(scale - value.scale)); const magnitude = normalized.reduce((maximum, value) => { const absolute = value < 0n ? -value : value; return absolute > maximum ? absolute : maximum; }, 1n);
  const heights = normalized.map((value) => { const absolute = value < 0n ? -value : value; return Math.max(2, Number(absolute * 42n / magnitude)); });
  const points = heights.map((height, index) => `${4 + index * (122 / Math.max(1, heights.length - 1))},${48-height}`).join(' ');
  if (form === 'line') return <svg width="130" height="50"><polyline points={points} fill="none" stroke="#81d4fa" strokeWidth="4" /></svg>;
  if (form === 'area') return <svg width="130" height="50"><polygon points={`${points} 126,48 4,48`} fill="#4fc3f799" /></svg>;
  if (form === 'bar' || form === 'stacked') return <svg width="130" height="50">{heights.map((height, index) => <rect key={index} x={index * (126 / heights.length) + 4} y={48-height} width={Math.max(4, 110 / heights.length)} height={height} fill={form === 'stacked' && index % 2 ? '#ffcc80' : '#81d4fa'} />)}</svg>;
  if (form === 'waterfall') return <svg width="130" height="50">{heights.map((height, index) => <rect key={index} x={index * (126 / heights.length) + 4} y={normalized[index] < 0n ? 25 : 48-height} width={Math.max(4, 110 / heights.length)} height={height} fill={normalized[index] < 0n ? '#ef9a9a' : '#a5d6a7'} />)}</svg>;
  if (form === 'comparison') return <svg width="130" height="50">{heights.slice(0,2).map((height, index) => <rect key={index} x={index ? 79 : 5} y={48-height} width="44" height={height} fill={index ? '#ffcc80' : '#81d4fa'}/>)}</svg>;
  if (form === 'timeline') return <svg width="130" height="50"><line x1="5" y1="25" x2="125" y2="25" stroke="#81d4fa" strokeWidth="3"/>{values.map((_, index) => <circle key={index} cx={12 + index * (104 / Math.max(1, values.length - 1))} cy="25" r="7" fill="#ffcc80"/>)}</svg>;
  return <svg width="130" height="50"><circle cx="25" cy="25" r="10" fill="#81d4fa"/><circle cx="105" cy="25" r="10" fill="#ffcc80"/><line x1="35" y1="25" x2="95" y2="25" stroke="#e8eef8" strokeWidth="3"/></svg>;
};

export const VisualizationReplay: React.FC<VisualizationReplayPropsV1> = (raw) => {
  const props = parseVisualizationReplayProps(raw); const frame = useCurrentFrame();
  const active = props.stages.some((stage) => frame >= stage.start_frame && frame < stage.end_exclusive_frame);
  const opacity = active ? interpolate(frame % 12, [0, 11], [0.72, 1], {extrapolateLeft:'clamp', extrapolateRight:'clamp'}) : 1;
  return <AbsoluteFill style={{background:'#0d141e', color:'#e8eef8', padding:48, fontFamily:'KurguPhase5Noto', opacity}}>
    <div style={{fontSize:18, letterSpacing:1, color:'#9bb4d1'}}>{props.visualization_id}</div>
    <div style={{fontSize:22, marginTop:12, color:'#ffcc80'}}>{props.forms.map((form) => `${form.kind}:${form.form}`).join(' · ')}</div>
    <div style={{display:'flex', gap:12, marginTop:10}}>{props.forms.map((form) => <FormGeometry key={form.item_id} form={form.form} rows={props.rows} />)}</div>
    {props.rows.map((row, index) => <div key={row.element_id} style={{display:'flex', gap:18, marginTop:20 + index * 3, fontSize:34}}><span style={{color:'#81d4fa'}}>{row.value}</span><span>{row.label}</span></div>)}
    <div style={{position:'absolute', bottom:38, left:48, fontSize:16, color:'#b7c5d6'}}>{props.source_captions.map((caption) => caption.text).join(' · ')}</div>
  </AbsoluteFill>;
};

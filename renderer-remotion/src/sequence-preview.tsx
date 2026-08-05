import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate, staticFile} from 'remotion';
import {tokens} from './design';
import type {ChartRevealDirective, RenderProps, VideoEvent} from './types';

const active = (events: VideoEvent[], frame: number) => events.filter((e) => e.start_frame <= frame && frame < e.end_exclusive_frame);
const Layer = ({children, z}: {children: React.ReactNode; z: number}) => <AbsoluteFill style={{zIndex:z, overflow:'hidden'}}>{children}</AbsoluteFill>;
/** Font-free, deterministic text surrogate. No host font discovery or glyph rasterization. */
const GlyphBars = ({value, color = '#fff', height = 34}: {value: string; color?: string; height?: number}) => <div aria-label={value} style={{display:'flex',gap:4,height,alignItems:'end'}}>{[...value].slice(0, 28).map((character, index) => <div key={`${index}-${character}`} style={{width:4 + (character.codePointAt(0) ?? 0) % 10,height:Math.max(7, height * (0.35 + ((character.codePointAt(0) ?? 0) % 65) / 100)),background:color}} />)}</div>;
const chartRevealAtFrame = (event: VideoEvent, directive: ChartRevealDirective | undefined, frame: number): number => {
  if (!directive) return 1_000_000;
  const span = event.end_exclusive_frame - event.start_frame;
  if (span === 1) return directive.reveal_end_millionths;
  const offset = Math.min(Math.max(frame - event.start_frame, 0), span - 1);
  const ratio = Math.floor(offset * 1_000_000 / (span - 1));
  return directive.reveal_start_millionths + Math.floor((directive.reveal_end_millionths - directive.reveal_start_millionths) * ratio / 1_000_000);
};
const sourceCrop = (event: VideoEvent) => {
  const source = event.payload.source;
  if (!source || typeof source !== 'object' || Array.isArray(source)) return null;
  const values = ['crop_left_millionths', 'crop_top_millionths', 'crop_right_millionths', 'crop_bottom_millionths'].map((key) => source[key]);
  if (!values.every((value) => typeof value === 'number' && Number.isInteger(value))) return null;
  const [left, top, right, bottom] = values as number[];
  if (left < 0 || top < 0 || left >= right || top >= bottom || right > 1_000_000 || bottom > 1_000_000) return null;
  return {left, top, right, bottom};
};
const fixtureAssetUrl = (contentHash: string) => staticFile(`phase4a-assets/${contentHash.slice('sha256:'.length)}.svg`);
export const SequencePreview: React.FC<RenderProps> = (props) => {
  const frame = useCurrentFrame(); const by = (track: string) => active(props.video_tracks.find((t) => t.track === track)?.events ?? [], frame);
  const v1 = by('V1'); const v2 = by('V2'); const v3 = by('V3'); const v4 = by('V4'); const v5 = by('V5'); const v6 = by('V6'); const v7 = by('V7');
  const directiveByEvent = new Map(props.visual_directives.map((directive) => [directive.event_id, directive]));
  const zoom = interpolate(frame, [0, Math.max(1, props.duration_frames - 1)], [1, 1.08], {extrapolateRight:'clamp'});
  const title = (event: VideoEvent | undefined, fallback: string) => String(event?.payload?.text ?? fallback);
  return <AbsoluteFill style={{background:tokens.background, color:'#fff'}}>
    <Layer z={1}><div style={{width:'100%',height:'100%',background:'linear-gradient(125deg,#263954,#10131b 70%)',transform:`scale(${zoom})`}} /><div style={{position:'absolute',left:80,top:84,maxWidth:900}}><GlyphBars value={title(v1[0], 'Sequence preview')} height={58}/></div></Layer>
    <Layer z={2}>{v2.map((e) => <div key={e.event_id} style={{position:'absolute',right:96,top:90,width:340,height:190,background:'#31516b',border:'2px solid #70d5e5',padding:22}}><GlyphBars value={e.editorial_role} height={28}/></div>)}</Layer>
    <Layer z={3}>{v3.map((e) => { const candidate = directiveByEvent.get(e.event_id); const directive = candidate?.kind === 'SOURCE_ZOOM_HIGHLIGHT' ? candidate : undefined; const binding = props.asset_bindings.find((item) => item.event_id === e.event_id); const crop = sourceCrop(e); const progress = interpolate(frame,[e.start_frame,Math.max(e.start_frame + 1,e.end_exclusive_frame - 1)],[0,1],{extrapolateRight:'clamp'}); const zoom = directive ? interpolate(progress,[0,1],[directive.zoom_start_millionths / 1_000_000,directive.zoom_end_millionths / 1_000_000]) : 1; const left = directive ? directive.highlight_left_millionths / 10_000 : 4; const top = directive ? directive.highlight_top_millionths / 10_000 : 45; const right = directive ? directive.highlight_right_millionths / 10_000 : 96; const bottom = directive ? directive.highlight_bottom_millionths / 10_000 : 62; const cropWidth = crop ? crop.right - crop.left : 1_000_000; const cropHeight = crop ? crop.bottom - crop.top : 1_000_000; return <div key={e.event_id} style={{position:'absolute',left:118,top:235,width:720,height:320,overflow:'hidden',background:tokens.document,border:'8px solid #d7d0bc',transform:`translateX(${interpolate(frame,[e.start_frame,e.end_exclusive_frame],[0,16],{extrapolateRight:'clamp'})}px) scale(${1.04 * zoom})`}}>{binding && <img aria-label={`trusted fixture ${binding.fixture_asset_id}`} src={fixtureAssetUrl(binding.content_sha256)} style={{position:'absolute',width:`${100_000_000 / cropWidth}%`,height:`${100_000_000 / cropHeight}%`,left:`${-100 * (crop?.left ?? 0) / cropWidth}%`,top:`${-100 * (crop?.top ?? 0) / cropHeight}%`,objectFit:'fill'}} />}<div style={{position:'absolute',inset:0,background:'linear-gradient(90deg,rgba(242,239,229,.04),rgba(242,239,229,.42))'}} />{directive && <div style={{position:'absolute',left:`${left}%`,top:`${top}%`,width:`${right-left}%`,height:`${bottom-top}%`,border:'5px solid #f6ce52',boxSizing:'border-box',pointerEvents:'none'}} />}</div>; })}</Layer>
    <Layer z={4}>{v4.map((e) => { const directive = directiveByEvent.get(e.event_id); const binding = props.asset_bindings.find((item) => item.event_id === e.event_id); const reveal = chartRevealAtFrame(e, directive?.kind === 'CHART_REVEAL' ? directive : undefined, frame); return <div key={e.event_id} style={{position:'absolute',right:104,bottom:145,width:380,height:250,overflow:'hidden',background:'#1c2635',borderLeft:'8px solid '+tokens.accent,padding:24}}>{binding && <img aria-label={`trusted fixture ${binding.fixture_asset_id}`} src={fixtureAssetUrl(binding.content_sha256)} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',clipPath:`inset(0 ${100 - reveal / 10_000}% 0 0)`}} />}<div style={{position:'relative'}}><GlyphBars value={'CHART EXPLAINER'} color={tokens.muted} height={18}/><div style={{display:'flex',alignItems:'end',gap:18,height:155,clipPath:`inset(0 ${100 - reveal / 10_000}% 0 0)`}}>{[52,94,126,178].map((h,i)=><div key={i} style={{width:48,height:h,background:tokens.evidenceYellow}} />)}</div></div></div>; })}</Layer>
    <Layer z={5}>{v5.map((e) => <div key={e.event_id} style={{position:'absolute',left:82,top:530}}><GlyphBars value={title(e, 'Key idea')} color={tokens.evidenceYellow} height={46}/></div>)}</Layer>
    <Layer z={6}>{v6.map((e) => <div key={e.event_id} style={{position:'absolute',left:120,right:120,bottom:tokens.captionSafeBottom,display:'flex',justifyContent:'center'}}><GlyphBars value={title(e, 'Word-cued caption')} height={34}/></div>)}</Layer>
    <Layer z={7}>{v7.map((e) => <div key={e.event_id} style={{position:'absolute',right:44,bottom:32}}><GlyphBars value={title(e, 'KURGU')} color={tokens.muted} height={16}/></div>)}</Layer>
  </AbsoluteFill>;
};

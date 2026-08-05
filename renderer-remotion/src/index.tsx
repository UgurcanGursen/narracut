import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {SequencePreview} from './sequence-preview';
import {COMPOSITION_ID} from './composition-registry';
import {parseRenderProps} from './schema';
import type {RenderProps} from './types';

const emptyVideo = ['V1','V2','V3','V4','V5','V6','V7'].map((track, priority) => ({track, kind:'VIDEO', priority, events:[]}));
const emptyAudio = ['A1','A2','A3','A4','A5'].map((track, priority) => ({track, priority, events:[]}));
const DEFAULT_PROPS: RenderProps = {schema_version:'RENDER-PROPS-V1',hash_scope_version:'RENDER-PROPS-HASH-V1',render_props_id:'rprops_preview',render_props_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',render_request_id:'rrq_preview',mode:'PREVIEW',renderer_version:'RRV1|bridge=0.0.0|package_lock_sha256=0000000000000000000000000000000000000000000000000000000000000000',project_id:'project_preview',document_id:'document_preview',narration_revision_id:'revision_preview',sequence_id:'sequence_preview',video_edl_id:'vedl_preview',video_edl_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',audio_edl_id:'aedl_preview',audio_edl_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',word_to_frame_id:'wtf_preview',word_to_frame_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',fps_numerator:30,fps_denominator:1,duration_frames:1,duration_samples:1600,width:1280,height:720,pixel_format:'rgba',composition_id:'sequence-preview-v1',design_system_version:'DESIGN-TOKENS-V1',fixture_manifest_id:'fixture_preview',fixture_manifest_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',video_tracks:emptyVideo,audio_tracks:emptyAudio,audio_boundary_decisions:[],asset_bindings:[],visual_directives:[]};
const Root: React.FC = () => <Composition id={COMPOSITION_ID} component={SequencePreview as unknown as React.ComponentType<Record<string, unknown>>} width={1280} height={720} fps={30} durationInFrames={1} defaultProps={DEFAULT_PROPS} calculateMetadata={({props}) => { const p=parseRenderProps(props); return {durationInFrames:p.duration_frames, fps:p.fps_numerator / p.fps_denominator, width:1280, height:720}; }} />;
registerRoot(Root);

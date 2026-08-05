import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {VisualizationReplay} from './visualization-replay';

const defaults = {schema_version:'VISUALIZATION-REPLAY-PROPS-V1',visualization_id:'viz_preview',visualization_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',render_plan_id:'vizplan_preview',render_plan_hash:'sha256:0000000000000000000000000000000000000000000000000000000000000000',width:1280,height:720,duration_in_frames:1,forms:[],rows:[],source_captions:[],stages:[]};
const Root: React.FC = () => <Composition id="visualization-replay-v1" component={VisualizationReplay as unknown as React.ComponentType<Record<string, unknown>>} width={1280} height={720} fps={30} durationInFrames={1} defaultProps={defaults} calculateMetadata={({props}) => { const input = props as typeof defaults; return {width:input.width, height:input.height, fps:30, durationInFrames:input.duration_in_frames}; }} />;
registerRoot(Root);

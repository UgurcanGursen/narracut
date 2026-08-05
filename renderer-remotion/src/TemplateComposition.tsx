import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, Sequence, cancelRender, continueRender, delayRender, staticFile} from 'remotion';
import {TEMPLATE_COMPONENTS} from './templates';
import type {TemplateRenderInputV1} from './template-contract';
import {verifyTemplateRenderInputIdentity} from './template-schema';

/** Projection only: all contract decisions have been made by the closed ingress. */
const Phase5FontFace: React.FC = () => <style>{`@font-face { font-family: 'KurguPhase5Noto'; src: url('${staticFile('phase5-fonts/NotoSans-Variable.ttf')}') format('truetype'); font-style: normal; font-weight: 100 900; font-display: block; }`}</style>;

export const TemplateComposition: React.FC<TemplateRenderInputV1> = (input) => {
  const [verified, setVerified] = useState(false);
  const handle = useMemo(() => delayRender('verify Phase 5 template input identity'), []);
  useEffect(() => { let active = true; Promise.all([verifyTemplateRenderInputIdentity(input), document.fonts.load('400 16px KurguPhase5Noto')]).then(() => { if (active) { setVerified(true); continueRender(handle); } }).catch((error: unknown) => cancelRender(error)); return () => { active = false; }; }, [handle, input]);
  if (!verified) return <AbsoluteFill style={{background:'#0d141e'}}><Phase5FontFace /></AbsoluteFill>;
  return <AbsoluteFill style={{background:'#0d141e'}}><Phase5FontFace />{input.template_render_plan.invocations.map((invocation,index) => {
  const Component=TEMPLATE_COMPONENTS[invocation.template_id];
  const binding=invocation.source_event_id === null ? undefined : input.render_props.asset_bindings.find((item)=>item.event_id===invocation.source_event_id);
  return <Sequence key={`${invocation.template_id}-${index}-${invocation.start_frame}`} from={invocation.start_frame} durationInFrames={invocation.end_exclusive_frame-invocation.start_frame}><Component invocation={invocation} assetHash={binding?.content_sha256 ?? null} /></Sequence>;
})}</AbsoluteFill>;
};

import type {RenderProps} from './types';
import {SequencePreview} from './sequence-preview';

export const COMPOSITION_ID = 'sequence-preview-v1' as const;
export const compositionRegistry = Object.freeze({
  [COMPOSITION_ID]: {width: 1280, height: 720, propsSchema: 'RENDER-PROPS-V1', component: SequencePreview},
});
export const resolveComposition = (id: string, props: RenderProps) => {
  if (id !== COMPOSITION_ID || props.composition_id !== COMPOSITION_ID) throw new Error('UNSUPPORTED_COMPOSITION');
  return compositionRegistry[COMPOSITION_ID];
};

/**
 * Pipeline stage model for the generation progress display.
 *
 * The stage list, their order and their weights mirror `BASE_STAGES` and
 * `AI_STAGES` in `backend/services/pipeline.py`. The backend reports a single
 * 0-100 number, so the split back into per-stage state has to use the same
 * weights, otherwise the checklist marks stages done at the wrong moment.
 */

export type StageStatus = 'pending' | 'active' | 'completed' | 'error'

export interface StageProgress {
  /** Stage identifier, matching the backend stage key. */
  key: string
  /** Suffix of the `generation.progress.*` i18n key. */
  labelKey: string
  status: StageStatus
  /** Completion of the active stage, 0-100. Only set while `status` is 'active'. */
  progress?: number
}

interface StageDefinition {
  key: string
  labelKey: string
  /** Share of total progress, copied from the backend stage table. */
  weight: number
}

/** Always executed. Mirrors `BASE_STAGES`. */
const BASE_STAGES: readonly StageDefinition[] = [
  { key: 'validate', labelKey: 'validating', weight: 5 },
  { key: 'fetch_dem', labelKey: 'downloadingDEM', weight: 30 },
  { key: 'process_terrain', labelKey: 'processingTerrain', weight: 20 },
  { key: 'heightmap', labelKey: 'generatingHeightmap', weight: 20 },
  { key: 'preview', labelKey: 'renderingPreview', weight: 10 },
  { key: 'package', labelKey: 'packaging', weight: 15 },
]

/** Inserted after the DEM download when AI segmentation is on. Mirrors `AI_STAGES`. */
const AI_STAGES: readonly StageDefinition[] = [
  { key: 'fetch_imagery', labelKey: 'downloadingImagery', weight: 15 },
  { key: 'segment', labelKey: 'aiSegmentation', weight: 20 },
  { key: 'vectorize', labelKey: 'extractingVectors', weight: 10 },
]

/**
 * The stage sequence for a run, matching the backend's
 * `BASE_STAGES[:2] + AI_STAGES + BASE_STAGES[2:]` splice.
 */
export function stagesFor(useAI: boolean): readonly StageDefinition[] {
  if (!useAI) {
    return BASE_STAGES
  }
  return [...BASE_STAGES.slice(0, 2), ...AI_STAGES, ...BASE_STAGES.slice(2)]
}

/**
 * Split an overall 0-100 percentage into per-stage state.
 *
 * Stages that the percentage has passed are 'completed', the one containing it
 * is 'active' (carrying its own 0-100 completion), and the rest are 'pending'.
 * When `failed` is set the active stage becomes 'error' instead, so the
 * checklist shows where the run stopped rather than a stalled spinner.
 */
export function computeStageProgress(
  percent: number,
  useAI: boolean,
  failed = false,
): StageProgress[] {
  const stages = stagesFor(useAI)
  const totalWeight = stages.reduce((sum, stage) => sum + stage.weight, 0) || 1
  const overall = Math.min(Math.max(Number.isFinite(percent) ? percent : 0, 0), 100)

  let consumedWeight = 0
  let activeAssigned = false

  return stages.map((stage) => {
    const start = (consumedWeight / totalWeight) * 100
    consumedWeight += stage.weight
    const end = (consumedWeight / totalWeight) * 100

    if (overall >= end) {
      return { key: stage.key, labelKey: stage.labelKey, status: 'completed' }
    }

    if (activeAssigned) {
      return { key: stage.key, labelKey: stage.labelKey, status: 'pending' }
    }

    activeAssigned = true
    if (failed) {
      return { key: stage.key, labelKey: stage.labelKey, status: 'error' }
    }

    const span = end - start
    const within = span > 0 ? ((overall - start) / span) * 100 : 0
    return {
      key: stage.key,
      labelKey: stage.labelKey,
      status: 'active',
      progress: Math.round(Math.min(Math.max(within, 0), 100)),
    }
  })
}

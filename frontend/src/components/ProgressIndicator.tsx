import { Check, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import type { StageProgress } from '../lib/stages'

interface ProgressIndicatorProps {
  steps: StageProgress[]
  currentMessage?: string
}

const STATUS_TEXT_CLASS: Record<StageProgress['status'], string> = {
  completed: 'text-green-400',
  active: 'text-blue-400',
  error: 'text-red-400',
  pending: 'text-gray-400',
}

const CONNECTOR_CLASS: Record<StageProgress['status'], string> = {
  completed: 'bg-green-500',
  active: 'bg-blue-500',
  error: 'bg-red-500',
  pending: 'bg-gray-600',
}

function StatusIcon({ status }: { status: StageProgress['status'] }) {
  if (status === 'completed') {
    return (
      <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
        <Check size={16} className="text-white" />
      </div>
    )
  }
  if (status === 'active') {
    return (
      <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
        <Loader2 size={16} className="text-white animate-spin" />
      </div>
    )
  }
  if (status === 'error') {
    return (
      <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
        !
      </div>
    )
  }
  return <div className="w-6 h-6 bg-gray-600 rounded-full border-2 border-gray-500" />
}

/**
 * Renders pipeline stages as a vertical checklist.
 *
 * Labels come from i18n. The previous version carried its own inline
 * `{ en, ru }` dictionary and picked between them by comparing
 * `t('common.language')` to the string `'ru'`, which bypassed i18next entirely
 * and meant adding a third language required editing this component.
 */
export const ProgressIndicator = ({ steps, currentMessage }: ProgressIndicatorProps) => {
  const { t } = useTranslation()

  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step.key} className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            <StatusIcon status={step.status} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-sm font-medium ${STATUS_TEXT_CLASS[step.status]}`}>
                {t(`generation.progress.${step.labelKey}`, { defaultValue: step.key })}
              </span>
              {step.status === 'active' && step.progress !== undefined && (
                <span className="text-xs text-blue-400 font-semibold">{step.progress}%</span>
              )}
            </div>

            {step.status === 'active' && step.progress !== undefined && (
              <div
                className="h-1.5 bg-gray-700 rounded-full overflow-hidden"
                role="progressbar"
                aria-valuenow={step.progress}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full bg-blue-500 transition-all duration-300 ease-out"
                  style={{ width: `${step.progress}%` }}
                />
              </div>
            )}

            {index < steps.length - 1 && (
              <div className={`ml-3 mt-2 w-0.5 h-6 ${CONNECTOR_CLASS[step.status]}`} />
            )}
          </div>
        </div>
      ))}

      {currentMessage && (
        <div className="mt-4 p-3 bg-blue-900/30 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-300 italic">{currentMessage}</p>
        </div>
      )}
    </div>
  )
}

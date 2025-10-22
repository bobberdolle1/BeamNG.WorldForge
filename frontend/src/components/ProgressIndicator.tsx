import { Check, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ProgressStep {
  id: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  progress?: number; // 0-100
}

interface ProgressIndicatorProps {
  steps: ProgressStep[];
  currentMessage?: string;
}

export const ProgressIndicator = ({ steps, currentMessage }: ProgressIndicatorProps) => {
  const { t } = useTranslation();

  const stepLabels: { [key: string]: { en: string; ru: string } } = {
    'validate': { en: 'Validating parameters', ru: 'Проверка параметров' },
    'fetch_dem': { en: 'Downloading DEM data', ru: 'Загрузка DEM данных' },
    'fetch_imagery': { en: 'Downloading satellite imagery', ru: 'Загрузка спутниковых снимков' },
    'process_terrain': { en: 'Processing terrain', ru: 'Обработка рельефа' },
    'segment_features': { en: 'Detecting features (AI)', ru: 'Распознавание объектов (AI)' },
    'generate_roads': { en: 'Generating roads', ru: 'Генерация дорог' },
    'generate_buildings': { en: 'Generating buildings', ru: 'Генерация зданий' },
    'generate_jbeam': { en: 'Creating JBeam code', ru: 'Создание JBeam кода' },
    'package': { en: 'Packaging map', ru: 'Упаковка карты' }
  };

  const getStepLabel = (id: string) => {
    const label = stepLabels[id];
    if (!label) return id;
    return t('common.language') === 'ru' ? label.ru : label.en;
  };

  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-start gap-3">
          {/* Status Icon */}
          <div className="flex-shrink-0 mt-1">
            {step.status === 'completed' ? (
              <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                <Check size={16} className="text-white" />
              </div>
            ) : step.status === 'active' ? (
              <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                <Loader2 size={16} className="text-white animate-spin" />
              </div>
            ) : step.status === 'error' ? (
              <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                !
              </div>
            ) : (
              <div className="w-6 h-6 bg-gray-600 rounded-full border-2 border-gray-500" />
            )}
          </div>

          {/* Step Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-sm font-medium ${
                step.status === 'completed' ? 'text-green-400' :
                step.status === 'active' ? 'text-blue-400' :
                step.status === 'error' ? 'text-red-400' :
                'text-gray-400'
              }`}>
                {getStepLabel(step.id)}
              </span>
              {step.progress !== undefined && step.status === 'active' && (
                <span className="text-xs text-blue-400 font-semibold">
                  {step.progress}%
                </span>
              )}
            </div>

            {/* Progress Bar */}
            {step.progress !== undefined && step.status === 'active' && (
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300 ease-out"
                  style={{ width: `${step.progress}%` }}
                />
              </div>
            )}

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div className={`ml-3 mt-2 w-0.5 h-6 ${
                step.status === 'completed' ? 'bg-green-500' :
                step.status === 'active' ? 'bg-blue-500' :
                'bg-gray-600'
              }`} />
            )}
          </div>
        </div>
      ))}

      {/* Current Message */}
      {currentMessage && (
        <div className="mt-4 p-3 bg-blue-900/30 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-300 italic">{currentMessage}</p>
        </div>
      )}
    </div>
  );
};

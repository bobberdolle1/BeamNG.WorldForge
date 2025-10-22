import { Map, Globe, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from './LanguageSwitcher'

interface HeaderProps {
  onNavigate?: (page: 'map' | 'settings') => void;
  currentPage?: 'map' | 'settings';
}

export default function Header({ onNavigate, currentPage = 'map' }: HeaderProps) {
  const { t } = useTranslation();
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-primary-600 p-2 rounded-lg">
            <Globe className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">{t('app.title')}</h1>
            <p className="text-sm text-gray-400">{t('app.subtitle')}</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {onNavigate && (
            <>
              <button
                onClick={() => onNavigate('map')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                  currentPage === 'map'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <Map size={18} />
                {t('nav.map')}
              </button>
              <button
                onClick={() => onNavigate('settings')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                  currentPage === 'settings'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <Settings size={18} />
                {t('nav.settings')}
              </button>
            </>
          )}
          <LanguageSwitcher />
          <span className="px-3 py-1 bg-blue-900 text-blue-200 text-xs font-semibold rounded-full">
            {t('app.version')}
          </span>
        </div>
      </div>
    </header>
  )
}


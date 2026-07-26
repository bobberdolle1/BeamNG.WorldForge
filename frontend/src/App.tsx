import { useCallback, useState } from 'react'

import GenerationPanel from './components/GenerationPanel'
import Header from './components/Header'
import MapSelector from './components/MapSelector'
import { SettingsPage } from './pages/SettingsPage'
import type { BoundingBox, GenerationStatus } from './types'

type Page = 'map' | 'settings'

function App() {
  const [selectedBBox, setSelectedBBox] = useState<BoundingBox | null>(null)
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null)
  const [currentPage, setCurrentPage] = useState<Page>('map')

  // Stable identity: GenerationPanel calls this from an effect, and a new
  // function on every render would make that effect fire every render.
  const handleStatusChange = useCallback((status: GenerationStatus | null) => {
    setGenerationStatus(status)
  }, [])

  const isGenerating =
    generationStatus?.status === 'processing' || generationStatus?.status === 'queued'

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      <Header onNavigate={setCurrentPage} currentPage={currentPage} />

      {currentPage === 'settings' ? (
        <SettingsPage />
      ) : (
        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 relative">
            <MapSelector onBBoxSelected={setSelectedBBox} disabled={isGenerating} />
          </div>

          <div className="w-96 bg-gray-800 border-l border-gray-700 overflow-y-auto">
            <GenerationPanel
              selectedBBox={selectedBBox}
              onStatusChange={handleStatusChange}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default App

import { useState } from 'react'
import MapSelector from './components/MapSelector'
import GenerationPanel from './components/GenerationPanel'
import Header from './components/Header'
import { SettingsPage } from './pages/SettingsPage'
import { BoundingBox, GenerationStatus } from './types'

function App() {
  const [selectedBBox, setSelectedBBox] = useState<BoundingBox | null>(null)
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null)
  const [currentPage, setCurrentPage] = useState<'map' | 'settings'>('map')

  if (currentPage === 'settings') {
    return (
      <div className="flex flex-col h-screen bg-gray-900">
        <Header onNavigate={setCurrentPage} currentPage={currentPage} />
        <SettingsPage />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      <Header onNavigate={setCurrentPage} currentPage={currentPage} />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Map Selector - Left Panel */}
        <div className="flex-1 relative">
          <MapSelector 
            onBBoxSelected={setSelectedBBox}
            disabled={generationStatus?.status === 'processing'}
          />
        </div>

        {/* Generation Panel - Right Sidebar */}
        <div className="w-96 bg-gray-800 border-l border-gray-700 overflow-y-auto">
          <GenerationPanel
            selectedBBox={selectedBBox}
            generationStatus={generationStatus}
            onGenerationStart={setGenerationStatus}
          />
        </div>
      </div>
    </div>
  )
}

export default App


import { Map, Globe } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-primary-600 p-2 rounded-lg">
            <Globe className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">BeamNG.WorldForge</h1>
            <p className="text-sm text-gray-400">Generate Maps from Satellite Data</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <span className="px-3 py-1 bg-blue-900 text-blue-200 text-xs font-semibold rounded-full">
            MVP v0.1.0
          </span>
          <Map className="w-5 h-5 text-gray-400" />
        </div>
      </div>
    </header>
  )
}


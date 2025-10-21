import { useState } from 'react';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { Scene3D } from './3d/Scene3D';
import { Terrain3D } from './3d/Terrain3D';
import { Roads3D } from './3d/Roads3D';
import { Buildings3D } from './3d/Buildings3D';

interface PreviewPanelProps {
  isOpen: boolean;
  onClose: () => void;
  mapData?: {
    heightmapUrl: string;
    roads?: any[];
    buildings?: any[];
    mapBounds?: {
      minLat: number;
      maxLat: number;
      minLon: number;
      maxLon: number;
    };
    mapSize?: number;
  };
}

export const PreviewPanel: React.FC<PreviewPanelProps> = ({ isOpen, onClose, mapData }) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showTerrain, setShowTerrain] = useState(true);
  const [showRoads, setShowRoads] = useState(true);
  const [showBuildings, setShowBuildings] = useState(true);
  
  if (!isOpen) return null;
  
  return (
    <div className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4`}>
      <div className={`bg-white rounded-lg shadow-2xl ${isFullscreen ? 'w-full h-full' : 'w-[90%] h-[80%]'} flex flex-col`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold">🎮 3D Preview</h2>
            
            {/* View Toggle Buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowTerrain(!showTerrain)}
                className={`px-3 py-1 rounded text-sm ${showTerrain ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                🏔️ Terrain
              </button>
              <button
                onClick={() => setShowRoads(!showRoads)}
                className={`px-3 py-1 rounded text-sm ${showRoads ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                🛣️ Roads
              </button>
              <button
                onClick={() => setShowBuildings(!showBuildings)}
                className={`px-3 py-1 rounded text-sm ${showBuildings ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              >
                🏢 Buildings
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 hover:bg-gray-100 rounded-full"
              title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
            >
              {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full"
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>
        
        {/* 3D Viewport */}
        <div className="flex-1 relative">
          {mapData ? (
            <Scene3D>
              {showTerrain && mapData.heightmapUrl && (
                <Terrain3D
                  heightmapUrl={mapData.heightmapUrl}
                  size={mapData.mapSize || 100}
                  heightScale={20}
                  resolution={128}
                />
              )}
              
              {showRoads && mapData.roads && mapData.roads.length > 0 && mapData.mapBounds && (
                <Roads3D
                  roads={mapData.roads}
                  mapBounds={mapData.mapBounds}
                  mapSize={mapData.mapSize || 100}
                />
              )}
              
              {showBuildings && mapData.buildings && mapData.buildings.length > 0 && mapData.mapBounds && (
                <Buildings3D
                  buildings={mapData.buildings}
                  mapBounds={mapData.mapBounds}
                  mapSize={mapData.mapSize || 100}
                />
              )}
            </Scene3D>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-6xl mb-4">🎮</div>
                <h3 className="text-xl font-bold mb-2">No Map Data</h3>
                <p className="text-gray-600">Generate a map first to see the 3D preview</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Footer with instructions */}
        <div className="p-4 border-t bg-gray-50 text-sm text-gray-600">
          <div className="flex gap-6">
            <div><strong>Left Mouse:</strong> Rotate</div>
            <div><strong>Right Mouse:</strong> Pan</div>
            <div><strong>Scroll:</strong> Zoom</div>
          </div>
        </div>
      </div>
    </div>
  );
};


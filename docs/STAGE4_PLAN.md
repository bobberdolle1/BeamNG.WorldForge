# BeamNG.WorldForge - Этап 4: 3D Preview & Traffic Simulation

**Дата начала:** 21 октября 2025  
**Версия:** 0.4.0 (planned)  
**Статус:** 🔄 В разработке

---

## 🎯 Цели этапа 4

Добавить интерактивный 3D preview генерируемых карт прямо в браузере с использованием **Three.js**, а также базовую симуляцию трафика для визуализации движения автомобилей по сгенерированным дорогам.

## 📋 Задачи

### 1. Three.js Integration
- [ ] Установка Three.js и необходимых зависимостей
- [ ] Создание 3D viewport компонента
- [ ] Настройка scene, camera, renderer
- [ ] Добавление OrbitControls для навигации
- [ ] Настройка освещения (ambient, directional)

### 2. Heightmap 3D Visualization
- [ ] Загрузка heightmap PNG в Three.js
- [ ] Генерация PlaneGeometry на основе heightmap
- [ ] Применение displacement mapping
- [ ] Настройка материалов для terrain (PBR)
- [ ] LOD оптимизация для больших карт
- [ ] Цветовая карта высот (color gradient)

### 3. Roads 3D Visualization
- [ ] Парсинг GeoJSON дорог
- [ ] Отрисовка дорог как 3D линий
- [ ] Экструзия дорог в 3D meshes
- [ ] Применение дорожных текстур
- [ ] Дорожная разметка (lanes)

### 4. Buildings 3D Visualization
- [ ] Загрузка building footprints из GeoJSON
- [ ] Экструзия зданий на правильную высоту
- [ ] Размещение зданий на terrain
- [ ] Простые фасады с окнами
- [ ] Материалы для зданий

### 5. Camera & Controls
- [ ] Free camera (OrbitControls)
- [ ] First-person camera
- [ ] Follow road camera (опционально)
- [ ] Preset camera positions
- [ ] Smooth camera transitions

### 6. Traffic Simulation
- [ ] Простая модель автомобиля (3D model или placeholder)
- [ ] Движение вдоль дорожных centerlines
- [ ] Управление скоростью
- [ ] Избегание столкновений (базовое)
- [ ] Spawn/despawn автомобилей
- [ ] Визуализация traffic flow

### 7. UI Integration
- [ ] 3D Preview Panel в GenerationPanel
- [ ] Кнопка "Open 3D Preview"
- [ ] Fullscreen mode для preview
- [ ] Controls panel (camera, traffic, settings)
- [ ] Loading states для 3D ресурсов
- [ ] Performance stats (FPS counter)

### 8. Materials & Lighting
- [ ] PBR materials для terrain
- [ ] Day/Night cycle (опционально)
- [ ] Shadows (CSM - Cascaded Shadow Maps)
- [ ] Fog для атмосферы
- [ ] Sky box или gradient background

---

## 🔧 Технические детали

### Three.js Stack

```typescript
Dependencies:
- three: ^0.160.0
- @react-three/fiber: ^8.15.0 (React Three Fiber)
- @react-three/drei: ^9.92.0 (Helpers)
- @types/three: ^0.160.0
```

**Почему React Three Fiber?**
- Декларативный подход
- React-friendly API
- Отличная интеграция с React
- Меньше boilerplate кода
- Automatic cleanup

### Architecture

```
frontend/src/
├── components/
│   ├── 3d/                    # 3D компоненты
│   │   ├── Scene3D.tsx        # Main 3D scene
│   │   ├── Terrain3D.tsx      # Terrain mesh
│   │   ├── Roads3D.tsx        # Roads visualization
│   │   ├── Buildings3D.tsx    # Buildings meshes
│   │   ├── TrafficSim.tsx     # Traffic simulation
│   │   ├── Camera3D.tsx       # Camera controller
│   │   └── Lighting3D.tsx     # Lights setup
│   ├── PreviewPanel.tsx       # 3D preview UI
│   └── ...
├── services/
│   ├── 3d/
│   │   ├── terrainLoader.ts   # Load heightmap
│   │   ├── roadBuilder.ts     # Build road meshes
│   │   ├── buildingBuilder.ts # Build building meshes
│   │   └── trafficManager.ts  # Traffic simulation logic
│   └── ...
└── utils/
    ├── geoUtils.ts            # Geo coordinate conversion
    └── threeMath.ts           # Three.js helpers
```

---

## 🎨 3D Preview Features

### Terrain Rendering

```typescript
// Heightmap → PlaneGeometry with displacement
const terrainGeometry = new THREE.PlaneGeometry(
  mapSize, mapSize, 
  resolution, resolution
);

// Apply heightmap as displacement
const displacementTexture = textureLoader.load(heightmapURL);
const material = new THREE.MeshStandardMaterial({
  map: colorMap,
  displacementMap: displacementTexture,
  displacementScale: maxHeight,
  roughness: 0.8,
  metalness: 0.0
});
```

### Roads Visualization

```typescript
// GeoJSON → Three.js Line/Mesh
roads.forEach(road => {
  const points = road.centerline.map(([lat, lon]) => 
    latLonToLocal(lat, lon, mapBounds)
  );
  
  const curve = new THREE.CatmullRomCurve3(points);
  const geometry = new THREE.TubeGeometry(
    curve, 
    64,      // segments
    roadWidth,
    8,       // radial segments
    false    // closed
  );
  
  const mesh = new THREE.Mesh(geometry, roadMaterial);
  scene.add(mesh);
});
```

### Traffic Simulation

```typescript
class Vehicle {
  position: THREE.Vector3;
  direction: THREE.Vector3;
  speed: number;
  currentRoad: Road;
  distanceOnRoad: number;
  
  update(deltaTime: number) {
    // Move along road centerline
    this.distanceOnRoad += this.speed * deltaTime;
    
    // Update position from curve
    const t = this.distanceOnRoad / this.currentRoad.length;
    this.position.copy(this.currentRoad.curve.getPointAt(t));
    
    // Update direction
    this.direction.copy(this.currentRoad.curve.getTangentAt(t));
    
    // Transition to next road at end
    if (t >= 1.0) {
      this.transitionToNextRoad();
    }
  }
}
```

---

## 📊 UI Mockup

```
┌─────────────────────────────────────────────┐
│  [Generate Map]  [3D Preview] 🎮           │
├─────────────────────────────────────────────┤
│                                             │
│           ╔═══════════════════╗            │
│           ║                   ║            │
│           ║   3D VIEWPORT     ║            │
│           ║                   ║            │
│           ║  🏔️ Terrain       ║            │
│           ║  🛣️  Roads         ║            │
│           ║  🏢 Buildings      ║            │
│           ║  🚗 Traffic        ║            │
│           ║                   ║            │
│           ╚═══════════════════╝            │
│                                             │
│  Controls:                                  │
│  🎥 Camera: [Free] [FPS] [Top]             │
│  🚗 Traffic: [Off] [Light] [Heavy]         │
│  ⚙️ Settings: [Shadows] [Fog] [LOD]        │
│  📊 FPS: 60                                 │
└─────────────────────────────────────────────┘
```

---

## 🚀 Implementation Plan

### Week 1: Foundation
**Дни 1-2:** Three.js setup, базовая сцена
- Установка dependencies
- Создание Scene3D компонента
- Camera + OrbitControls
- Basic lighting

**Дни 3-4:** Terrain visualization
- Heightmap loading
- Displacement mapping
- Material setup
- Color gradient по высоте

**День 5:** Roads visualization (basic)
- Load GeoJSON
- Draw as lines
- Basic materials

### Week 2: Advanced Visualization
**Дни 6-7:** Roads 3D meshes
- Tube geometry для дорог
- Road textures
- Proper width и elevation

**Дни 8-9:** Buildings 3D
- Extrude footprints
- Place on terrain
- Basic facades

**День 10:** Materials & lighting
- PBR materials
- Shadows
- Atmospheric effects

### Week 3: Traffic Simulation
**Дни 11-13:** Traffic logic
- Vehicle class
- Path following
- Speed management
- Spawning system

**Дни 14-15:** Traffic visualization
- Vehicle models (простые)
- Movement animations
- Traffic flow control

### Week 4: Polish & Integration
**Дни 16-17:** UI integration
- PreviewPanel component
- Controls panel
- Loading states

**Дни 18-19:** Optimization
- LOD для terrain
- Frustum culling
- Instance rendering для vehicles

**Дни 20-21:** Testing & fixes
- Performance testing
- Bug fixes
- Documentation

---

## 🎯 Success Criteria

### Must Have:
- ✅ Terrain отображается из heightmap
- ✅ Дороги видны в 3D
- ✅ Здания размещены корректно
- ✅ Камера управляется плавно
- ✅ FPS > 30 на средних настройках

### Nice to Have:
- ⭐ Realistic materials
- ⭐ Shadows работают
- ⭐ Traffic simulation плавная
- ⭐ Multiple camera modes
- ⭐ Day/night cycle

### Optional:
- 🌟 Weather effects
- 🌟 Vegetation (trees)
- 🌟 Water bodies rendering
- 🌟 Minimap

---

## 📈 Performance Targets

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| FPS | 30+ | 60 |
| Terrain Resolution | 512x512 | 1024x1024 |
| Max Buildings | 200 | 500 |
| Max Vehicles | 10 | 50 |
| Load Time | <5s | <2s |

---

## 🔄 Data Flow

```
Backend generates:
├── heightmap.png
├── roads.geojson
├── buildings.geojson
└── metadata.json
     ↓
Frontend downloads
     ↓
3D Loaders:
├── terrainLoader → PlaneGeometry
├── roadBuilder → Tube/Line meshes
└── buildingBuilder → Extruded meshes
     ↓
Three.js Scene
     ↓
Render Loop (60 FPS)
├── Update traffic positions
├── Update camera
└── Render frame
```

---

## 🧪 Testing Strategy

### Visual Tests:
- Screenshot comparison
- Manual inspection
- Different map sizes

### Performance Tests:
- FPS monitoring
- Memory usage
- Load time benchmarks

### Integration Tests:
- Load real generated maps
- All features working together
- Edge cases (empty maps, large maps)

---

## 📚 Resources & References

### Three.js:
- [Three.js Documentation](https://threejs.org/docs/)
- [React Three Fiber](https://docs.pmnd.rs/react-three-fiber)
- [Three.js Examples](https://threejs.org/examples/)

### Terrain Rendering:
- Displacement mapping techniques
- LOD strategies
- Terrain texturing

### Traffic Simulation:
- Path following algorithms
- Collision avoidance
- Traffic flow models

---

## 🎓 Learning Outcomes

После завершения Этапа 4, вы узнаете:
- ✅ Three.js fundamentals
- ✅ React Three Fiber patterns
- ✅ 3D terrain rendering
- ✅ Path following algorithms
- ✅ Performance optimization для 3D
- ✅ Integration 3D в web apps

---

## 🔮 Future Enhancements (Этап 5)

После Этапа 4 можно добавить:
- Advanced traffic AI (lane changing, intersections)
- Weather system (rain, fog, snow)
- Time of day с realistic lighting
- Water rendering (rivers, lakes)
- Vegetation placement (trees, grass)
- Interactive mode (drive around)

---

**Ready to build amazing 3D preview!** 🚀🎮

*Next: Installing dependencies and creating first 3D scene*


"""
Turn detected vectors into BeamNG level content.

Everything here is deterministic. The LLM-based `services/code_generation`
package that used to sit alongside it asked a model to emit JBeam JSON and
COLLADA XML - fixed-schema documents that code generates correctly every time,
without a network call, an API key, or the chance of an invalid result. It has
been removed; `mesh_builder` carries forward the procedural extrusion that
package already used as its fallback.
"""

from .building_placer import BuildingPlacer
from .mesh_builder import MeshBuilder
from .road_builder import RoadBuilder

__all__ = ["BuildingPlacer", "MeshBuilder", "RoadBuilder"]

import math
from mathutils import Vector
from typing import List, Tuple, Dict, Optional


class ViewGenerator:
    def __init__(
        self,
        scene_center: Tuple[float, float, float] = (0, 0, 0),
        camera_distance: float = 5.0
    ):
        self.scene_center = Vector(scene_center)
        self.camera_distance = camera_distance

    def _compute_rotation(self, cam_loc: Vector) -> Tuple[float, float, float]:
        direction = self.scene_center - cam_loc
        quat = direction.to_track_quat('-Z', 'Y')
        e = quat.to_euler()
        return (e.x, e.y, e.z)

    def _make_view(
        self,
        name: str,
        cam_loc: Vector,
        visible_axes: List[str]
    ) -> Dict:
        """Pack position+rotation into the dict format."""
        rot = self._compute_rotation(cam_loc)
        return {
            'name':         name,
            'position':     (cam_loc.x, cam_loc.y, cam_loc.z),
            'rotation':     rot,
            'visible_axes': visible_axes
        }

    def circular(
        self,
        num_angles: int = 6,
        angles_to_render: Optional[List[int]] = None,
        elevation: float = 0.5
    ) -> List[Dict]:
        """Evenly spaced around Z at fixed elevation fraction."""
        if angles_to_render is None:
            angles_to_render = list(range(num_angles))

        views = []
        for i in angles_to_render:
            frac = i / num_angles
            θ = frac * math.pi * 2
            x = math.cos(θ) * self.camera_distance
            y = math.sin(θ) * self.camera_distance
            z = self.camera_distance * elevation
            loc = self.scene_center + Vector((x, y, z))
            views.append(self._make_view(f'circle_{i:02d}', loc, ['X','Y','Z']))
        return views

    def spherical(
        self,
        num_azimuth: int = 8,
        num_elevation: int = 4,
        azimuths: Optional[List[float]] = None,
        elevations: Optional[List[float]] = None
    ) -> List[Dict]:
        """Full-sphere sampling via (azimuth, elevation)."""

        if azimuths is None:
            azimuths = [i * 360.0 / num_azimuth for i in range(num_azimuth)]
        if elevations is None:
            # note: num_elevation−1 so you hit 0° and 180° exactly
            elevations = [i * 180.0 / (num_elevation - 1) for i in range(num_elevation)]

        # 2) convert degrees → radians for math.sin/cos
        az_rad = [math.radians(deg) for deg in azimuths]
        el_rad = [math.radians(deg) for deg in elevations]

        views = []
        for deg_el, φ in zip(elevations, el_rad):
            for deg_az, θ in zip(azimuths, az_rad):
                # spherical → Cartesian
                x = self.camera_distance * math.sin(φ) * math.cos(θ)
                y = self.camera_distance * math.sin(φ) * math.sin(θ)
                z = self.camera_distance * math.cos(φ)

                loc = self.scene_center + Vector((x, y, z))
                name = f'sphere_az{int(deg_az):03d}_el{int(deg_el):03d}'

                views.append(self._make_view(name, loc, ['X', 'Y', 'Z']))

        return views

    def orthographic(self) -> List[Dict]:
        """Front/side/top fixed views."""
        SC, D = self.scene_center, self.camera_distance
        return [
            self._make_view('front', SC + Vector((0, -D, 0)), ['X', 'Z']),
            self._make_view('side',  SC + Vector((D, 0, 0)), ['Y', 'Z']),
            self._make_view('top',   SC + Vector((0, 0, D)),  ['X', 'Y']),
        ]

    def generate(
        self,
        mode: str = 'sphere',
        **kwargs
    ) -> List[Dict]:
        """
        mode: 'circle', 'sphere', or '2d'
        kwargs are passed to the corresponding method.
        """
        fn_map = {
            'circle':     self.circular,
            '3d':         self.circular,
            'sphere':     self.spherical,
            '2d':         self.orthographic,
            'orthographic': self.orthographic
        }
        key = mode.lower()
        if key not in fn_map:
            raise ValueError(f"mode must be one of {list(fn_map)}")
        return fn_map[key](**kwargs)

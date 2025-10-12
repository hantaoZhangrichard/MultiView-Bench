import sys
import os
from mathutils import Vector
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from render import render_scene


class ViewNavigationEnv():
    def __init__(self, gltf_path, object_id, output_path):
        self.gltf_path = gltf_path
        self.object_id = object_id
        self.output_path = output_path
    
    def capture(self, azimuth, elevation):
        view_kwargs = {
            'azimuths': [azimuth],
            'elevations': [elevation]
        }
        args = (self.output_path, self.object_id, self.gltf_path)
        coords_center = Vector((0, 0, 0))
        render_scene(args, show_coords=True, show_grid=False, coords_center=coords_center, mode='3D', rotation_angle=0,
                 vg_mode="sphere", **view_kwargs)

        # Return image path
        return os.path.join(self.output_path, f"{self.object_id}_sphere_az{int(azimuth):03d}_el{int(elevation):03d}.png")
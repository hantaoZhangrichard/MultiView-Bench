import bpy
from mathutils import Vector
import math
import logging
import os
import time
from visual_enhance import create_scene_2D, create_scene_3D, create_grid_for_view
from view_generator import ViewGenerator

logger = logging.getLogger("render")


def calculate_scene_center():
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    if not mesh_objects:
        raise ValueError("No mesh objects found in the scene.")
    
    # Compute the centroid
    total_location = sum((obj.location for obj in mesh_objects), start=Vector((0, 0, 0)))
    center = total_location / len(mesh_objects)
    return center


def add_light_to_scene(scene_center, light_distance=3, light_strength=2000):
    # Add a light to the scene
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
    key_light = bpy.context.object
    key_light.location = (
        scene_center.x + light_distance / math.sqrt(2),  # 45-degree x offset
        scene_center.y - light_distance / math.sqrt(2),  # 45-degree y offset
        scene_center.z + light_distance                  # Above the scene
    )
    key_light.data.energy = light_strength  # Set the light strength

    key_light.rotation_euler = (math.radians(45), 0, math.radians(45))  # Point at the object

    bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
    fill_light = bpy.context.object
    fill_light.location = (
        scene_center.x - 1.5 * light_distance / math.sqrt(2),
        scene_center.y - 1.5 * light_distance / math.sqrt(2),
        scene_center.z + 1.5 * light_distance / 2
    )
    fill_light.data.energy = light_strength / 2

    bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
    back_light = bpy.context.object
    back_light.location = (
        scene_center.x,
        scene_center.y + 2 * light_distance,
        scene_center.z + light_distance
    )
    back_light.data.energy = 0.75 * light_strength


def add_sun_camera_light(camera, strength=5.0):
    # add a sun lamp at camera
    bpy.ops.object.light_add(type='SUN', location=camera.location)
    sun = bpy.context.object
    sun.data.energy = strength

    # point it in exactly the same direction as the camera
    sun.rotation_euler = camera.rotation_euler

    # parent so it follows the camera
    sun.parent = camera


def add_light_to_scene_camera_follow(camera, light_distance=3, light_strength=2000):
    # offets in CAMERA local coordinates
    offsets = {
        'key':   Vector((  light_distance/math.sqrt(2), 
                          -light_distance/math.sqrt(2), 
                           light_distance )),
        'fill':  Vector(( -1.5*light_distance/math.sqrt(2),
                          -1.5*light_distance/math.sqrt(2),
                           0.75*light_distance )),
        'back':  Vector(( 0,
                           2*light_distance,
                           light_distance ))
    }

    for name, off in offsets.items():
        # create the lamp
        bpy.ops.object.light_add(type='POINT', location=camera.location)
        lamp = bpy.context.object
        lamp.name = f"{name}_light"
        lamp.data.energy = light_strength * {
            'key': 1.0, 'fill': 0.5, 'back': 0.75
        }[name]

        # move it to camera-local offset
        world_pos = camera.matrix_world @ off
        lamp.location = world_pos

        # make the lamp follow the camera
        lamp.parent = camera


def set_render_config(resolution_w=720, resolution_h=720, num_sample=32):
    bpy.context.scene.render.resolution_x = resolution_w  # e.g., width
    bpy.context.scene.render.resolution_y = resolution_h   # e.g., height
    bpy.context.scene.render.resolution_percentage = 100
    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = num_sample


def apply_camera_rotation(views, rotation_angle):
    for view in views:
        # Convert tuple to list, modify, convert back to tuple
        rotation_list = list(view["rotation"])
        
        if view['name'] == 'front':
            rotation_list[1] += math.radians(rotation_angle)
        elif view['name'] == 'side':
            rotation_list[1] += math.radians(rotation_angle)
        elif view['name'] == 'top':
            rotation_list[2] += math.radians(rotation_angle)
        
        view["rotation"] = tuple(rotation_list)
    
    return views


def clear_coordinate_objects():
    """Remove all coordinate system objects from the scene."""
    objects_to_remove = []
    for obj in bpy.data.objects:
        if (obj.name.startswith("Axis_") or 
            obj.name.startswith("Origin_") or
            obj.name.startswith("Grid_") or
            obj.name.startswith("Coord_")):
            objects_to_remove.append(obj)
    
    for obj in objects_to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)


def clear_grid_objects():
    """Remove all grid objects from the scene"""
    objects_to_remove = []
    for obj in bpy.data.objects:
        if obj.name.startswith("Grid_"):
            objects_to_remove.append(obj)
    
    for obj in objects_to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)


def focus_camera_and_render(output_dir, object_id, camera_distance=5,
                            mode='3D',
                            show_coordinates=True,
                            show_grid=True,
                            opacity=0.3,
                            coords_center=None, 
                            rotation_angle=45,
                            vg_mode="circle",
                            **view_kwargs):
    # Calculate the center of the scene
    scene_center = calculate_scene_center()
    
    # Set coordinate system center (defaults to scene center)
    if coords_center is None:
        coords_center = scene_center

    # Ensure there is a camera in the scene
    if not any(obj.type == 'CAMERA' for obj in bpy.data.objects):
        bpy.ops.object.camera_add()
    
    camera = next(obj for obj in bpy.data.objects if obj.type == 'CAMERA')
    bpy.context.scene.camera = camera
    
    # Add light to the scene
    # add_light_to_scene(scene_center, light_distance=camera_distance)
    # add_world_light()
    add_sun_camera_light(camera, strength=3.0)

    # Set render settings
    set_render_config()

    # Generate views with ALL required parameters
    try:
        vg = ViewGenerator(scene_center=scene_center, camera_distance=camera_distance)
        views = vg.generate(mode=vg_mode, **view_kwargs)
    except Exception as e:
        logger.error(f"Error generating views: {str(e)}")
        raise

    try:
        # Apply rotation around view axis if specified
        if rotation_angle != 0:
            views = apply_camera_rotation(views, rotation_angle)
    except Exception as e:
        logger.error(f"Error: {str(e)}")

    for i in range(len(views)):
        
        # Clear any existing coordinate objects from previous views
        clear_coordinate_objects()
        clear_grid_objects()
        view = views[i]
        logger.info(f"Rendering view {i+1}/{len(views)}: {view['name']}")
        
        # Set camera position and rotation FIRST
        camera.location = view['position']
        camera.rotation_euler = view['rotation']

        visible_axes = view['visible_axes']

        if show_coordinates:
            if mode.upper() == "3D":
                create_scene_3D(scene_center=coords_center)
            elif mode.upper() == '2D':
                create_scene_2D(scene_center=coords_center, visible_axes=visible_axes,
                                camera_position=view['position'], rotation_angle=rotation_angle)
            else:
                raise ValueError(f"Invalid mode: {mode}. Must be '3D' or '2D'")
        
        if show_grid:
            create_grid_for_view(
                coords_center, 
                view['name'], 
                camera_distance=camera_distance,
                opacity=opacity
            )
        
        # Set render output path
        bpy.context.scene.render.filepath = os.path.join(
            output_dir,
            f"{object_id}_{view['name']}.png"
        )
        
        # Render the image
        bpy.ops.render.render(write_still=True)


def import_gltf(gltf_file_path):
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        bpy.ops.import_scene.gltf(filepath=gltf_file_path)
    except Exception:
        raise ValueError(f"File '{gltf_file_path}' not found.")

    
def render_scene(args, show_coords=True, show_grid=True, coords_center=None, mode='3D', rotation_angle=45,
                 vg_mode="circle", **view_kwargs):
    output_path, object_id, gltf_path = args
    try:
        import_gltf(gltf_path)
        focus_camera_and_render(output_dir=output_path, object_id=object_id,
                                mode=mode,
                                show_coordinates=show_coords,
                                show_grid=show_grid,
                                opacity=0.3,
                                coords_center=coords_center, 
                                rotation_angle=rotation_angle,
                                vg_mode=vg_mode,
                                **view_kwargs)
    except Exception as e:
        raise ValueError(f"Error rendering for {object_id}: {e}")


def render_scene_sequential(render_image_tasks, show_coords=True, show_grid=True, coords_center=None, mode='3D', rotation_angle=45,
                            vg_mode="circle", **view_kwargs):
    start_time = time.time()
    
    logger.info(f"Processing {len(render_image_tasks)} rendering tasks sequentially...")

    results = []
    for i, task in enumerate(render_image_tasks):
        logger.info(f"Processing task {i+1}/{len(render_image_tasks)}")
        try:
            render_scene(task, show_coords=show_coords, show_grid=show_grid, coords_center=coords_center, mode=mode, rotation_angle=rotation_angle,
                         vg_mode=vg_mode, **view_kwargs)
            results.append("success")
        except Exception as e:
            logger.error(f"Task {i+1} failed: {str(e)}")
            results.append("error")
    
    # Count successes and failures
    successes = sum(1 for r in results if r == "success")
    failures = sum(1 for r in results if r == "error")
    
    logger.info(f"Completed {len(results)} rendering tasks: {successes} successful, {failures} failed")
    end_time = time.time()
    logger.info(f"Total rendering time: {end_time - start_time:.2f} seconds")
    
    return results
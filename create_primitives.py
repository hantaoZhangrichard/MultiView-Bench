import bpy
import logging
from mathutils import Vector, Euler
import os

logger = logging.getLogger("create_primitives")


def create_cube(location=(0, 0, 0), scale=(1, 1, 1), name="Cube"):
    bpy.ops.mesh.primitive_cube_add(location=location, scale=scale)
    cube = bpy.context.active_object
    cube.name = name
    return cube


def create_sphere(location=(0, 0, 0), scale=(1, 1, 1), name="Sphere", subdivisions=2):
    try:
        # Create sphere with correct parameters
        bpy.ops.mesh.primitive_uv_sphere_add(
            location=location,
            segments=32,      # CORRECT: longitude segments
            ring_count=16     # CORRECT: latitude rings
        )
        
        sphere = bpy.context.active_object
        if sphere is None:
            logger.warning("Error: No active object after sphere creation")
            return None
            
        sphere.name = name
        
        # Apply scale after creation (not during creation)
        sphere.scale = scale
        
        # Add subdivision surface modifier for smoothness if requested
        if subdivisions > 0:
            modifier = sphere.modifiers.new(name="Subdivision", type='SUBSURF')
            modifier.levels = subdivisions
        
        logger.info(f"Successfully created sphere '{name}' at {location}")
        return sphere
        
    except Exception as e:
        logger.warning(f"Error creating sphere '{name}': {str(e)}")
        return None


def create_cone(location=(0, 0, 0), scale=(1, 1, 1), name="Cone", vertices=32, depth=2.0):
    try:
        bpy.ops.mesh.primitive_cone_add(
            location=location,
            vertices=vertices,
            depth=depth
        )
        
        cone = bpy.context.active_object
        cone.name = name
        cone.scale = scale
        
        logger.info(f"Successfully created cone '{name}' at {location}")
        return cone
        
    except Exception as e:
        logger.warning(f"Error creating cone '{name}': {str(e)}")
        return None


def create_cylinder(location=(0, 0, 0), scale=(1, 1, 1), name="Cylinder", vertices=32, depth=2.0):
    try:
        bpy.ops.mesh.primitive_cylinder_add(
            location=location,
            vertices=vertices,
            depth=depth
        )
        
        cylinder = bpy.context.active_object
        cylinder.name = name
        cylinder.scale = scale
        
        logger.info(f"Successfully created cylinder '{name}' at {location}")
        return cylinder
        
    except Exception as e:
        logger.warning(f"Error creating cylinder '{name}': {str(e)}")
        return None


def import_and_position_gltf_object(object_id, position, gltf_base_path, rotation=(0, 0, 0), scale=(1, 1, 1), 
                                   file_extension=".gltf"):
    # Construct the full file path
    gltf_file_path = os.path.join(gltf_base_path, f"{object_id}{file_extension}")
    
    # Check if file exists
    if not os.path.exists(gltf_file_path):
        logger.error(f"GLTF file not found: {gltf_file_path}")
        return None
    
    # Store current objects to identify newly imported ones
    objects_before = set(bpy.context.scene.objects)
    
    try:
        # Import the GLTF file
        bpy.ops.import_scene.gltf(filepath=gltf_file_path)
        logger.info(f"Successfully imported GLTF: {gltf_file_path}")
        
    except Exception as e:
        logger.error(f"Failed to import GLTF file {gltf_file_path}: {str(e)}")
        return None
    
    # Find newly imported objects (all parts of the object)
    objects_after = set(bpy.context.scene.objects)
    imported_objects = list(objects_after - objects_before)
    
    if not imported_objects:
        logger.warning(f"No objects were imported from {gltf_file_path}")
        return None
    
    logger.info(f"Imported {len(imported_objects)} parts for object '{object_id}': {[obj.name for obj in imported_objects]}")
    
    # Create a parent empty object to control all parts of the imported model
    parent_name = f"{object_id}"
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    parent_obj = bpy.context.active_object
    parent_obj.name = parent_name
    
    # Clear selection
    bpy.ops.object.select_all(action='DESELECT')
    
    # Parent all imported objects (parts) to the empty parent
    for obj in imported_objects:
        # Select the object to be parented
        obj.select_set(True)
        
    # Select the parent object last (it will be the active object)
    parent_obj.select_set(True)
    bpy.context.view_layer.objects.active = parent_obj
    
    # Set parent for all selected objects (all parts) with keep transform
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    
    logger.info(f"Parented {len(imported_objects)} parts to '{parent_name}'")
    
    # Apply transformations to the parent object (this moves all parts together)
    parent_obj.location = Vector(position)
    parent_obj.rotation_euler = Euler(rotation, 'XYZ')
    parent_obj.scale = Vector(scale)
    
    logger.info(f"Parent scale set to: {parent_obj.scale}")
    # Clear selection
    bpy.ops.object.select_all(action='DESELECT')
    
    logger.info(f"Positioned {object_id} at {position} with rotation {rotation} and scale {scale}")
    
    return parent_obj
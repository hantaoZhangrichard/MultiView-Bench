import logging
import bpy
from create_primitives import create_cone, create_sphere, create_cylinder, create_cube 
from create_primitives import import_and_position_gltf_object
from color_materials import create_colored_material

logger = logging.getLogger("add_objects")


def add_objects_to_scene(objects_dict, output_path, default_scale=(0.5, 0.5, 0.5), 
                        add_materials=True, default_opacity=0.3, color_map=None):
    # Mapping of string names to creation functions
    shape_functions = {
        'cube': create_cube,
        'sphere': create_sphere,
        'cone': create_cone,
        'cylinder': create_cylinder,
    }

    created_objects = {}

    for shape_name, location in objects_dict.items():
        shape_type = shape_name.lower()

        if shape_type in shape_functions:
            # Generate unique name for the object
            object_name = f"{shape_type.capitalize()}_{len(created_objects) + 1}"

            # Create the object using the appropriate function
            obj = shape_functions[shape_type](
                location=location,
                scale=default_scale,
                name=object_name
            )
            # Add default material if requested
            if add_materials:
                if color_map:
                    color = color_map.get(shape_type, (0.5, 0.5, 0.5))  # Gray fallback
                else:
                    color = (0.5, 0.5, 0.5)
                material = create_colored_material(
                    part_name=object_name,
                    color_map={object_name: color},
                    opacity=default_opacity
                )

                # Apply material to object
                if obj.data.materials:
                    obj.data.materials[0] = material
                else:
                    obj.data.materials.append(material)

                logger.info(f"Created {shape_type} at {location} with name '{object_name}' and material")
            else:
                logger.info(f"Created {shape_type} at {location} with name '{object_name}'")

            created_objects[object_name] = obj

        else:
            logger.warning(f"Warning: Unknown shape type '{shape_name}'. Supported types: {list(shape_functions.keys())}")

    # Export the updated scene to the output GLTF
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        use_selection=False,
        export_apply=True,
        export_format='GLTF_SEPARATE'
    )

    return created_objects


def add_objects_to_scene_real(objects_dict, output_path, default_rotation=(0, 0, 0), 
                             default_scale=(1, 1, 1), gltf_base_path="./models/", 
                             clear_existing=False, file_extension=".gltf",
                             add_materials=True, default_opacity=0.7, color_map=None):
    # Clear existing objects if requested
    if clear_existing:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        logger.info("Cleared existing objects from scene")

    created_objects = {}

    for object_id, transform_data in objects_dict.items():
        # Parse transform data - can be just position or (position, rotation, scale)
        if isinstance(transform_data, (tuple, list)) and len(transform_data) >= 3:
            # Check if it's a simple position tuple or complex transform
            if all(isinstance(x, (int, float)) for x in transform_data):
                # Simple position tuple
                position = transform_data
                rotation = default_rotation
                scale = default_scale
            else:
                # Complex transform tuple (position, rotation, scale)
                position = transform_data[0] if transform_data[0] is not None else (0, 0, 0)
                rotation = transform_data[1] if len(transform_data) > 1 and transform_data[1] is not None else default_rotation
                scale = transform_data[2] if len(transform_data) > 2 and transform_data[2] is not None else default_scale
        else:
            # Assume it's just a position
            position = transform_data
            rotation = default_rotation
            scale = default_scale

        # Import and position the object (with all its parts)
        parent_obj = import_and_position_gltf_object(
            object_id=object_id,
            position=position,
            rotation=rotation,
            scale=scale,
            gltf_base_path=gltf_base_path,
            file_extension=file_extension
        )

        if parent_obj:
            created_objects[object_id] = parent_obj

            # Apply materials if requested
            if add_materials:
                # Create material for this object using the existing function
                material = create_colored_material(
                    part_name=object_id,
                    color_map=color_map if color_map else {},
                    opacity=default_opacity
                )

                # Apply material to all mesh parts of the object
                for child in parent_obj.children:
                    if child.type == 'MESH' and child.data:
                        # Clear existing materials
                        child.data.materials.clear()
                        # Add the new material
                        child.data.materials.append(material)
                        logger.info(f"Applied material to mesh part: {child.name}")

                logger.info(f"Successfully added object '{object_id}' to scene with material")
            else:
                logger.info(f"Successfully added object '{object_id}' to scene")
        else:
            logger.error(f"Failed to add object '{object_id}' to scene")

    # Export the updated scene to the output GLTF
    try:
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            use_selection=False,
            export_apply=True,
            export_format='GLTF_SEPARATE'
        )
        logger.info(f"Scene exported successfully to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to export scene to {output_path}: {str(e)}")

    return created_objects


def empty_scene():
    """Thoroughly clean up the Blender scene to avoid memory buildup"""
    # Clear selection
    bpy.ops.object.select_all(action='DESELECT')

    # Select and remove all objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Clear mesh data that's no longer used
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    # Clear materials
    for material in bpy.data.materials:
        if material.users == 0:
            bpy.data.materials.remove(material)

    # Clear other potential data types as needed
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)

    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)

    # Purge all orphan data
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # Optional: manually call Blender's undo system flush
    try:
        bpy.ops.ed.undo_push(message="Cleanup")  # Push current state
        bpy.ops.ed.undo_flush()  # Flush undo stack
    except:
        pass  # Might not be available in all contexts
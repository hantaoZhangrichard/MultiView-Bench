import bpy
import mathutils
from mathutils import Vector, Matrix
import math
import logging

logger = logging.getLogger("visual_enhance")


def add_coordinate_axes(scene_center, axis_length=1.0, axis_thickness=0.02, 
                        visible_axes=["X", "Y", "Z"], materials=None):
    """
        scene_center: Vector
    """
    if not materials:
        materials = create_axes_material(visible_axes=visible_axes)
    
    # Arrow parameters
    cone_height = axis_length * 0.1  # Cone height as percentage of axis length
    cone_radius = axis_thickness * 3  # Cone radius relative to axis thickness
    cylinder_length = axis_length - cone_height  # Adjust cylinder length to account for cone
    
    # Create cylinder and cone for each axis with correct orientations
    # X = Red = Width (left/right), Y = Green = Depth (front/back), Z = Blue = Height (up/down)
    all_axes_data = {
        # X-axis: Red cylinder along X direction (left-right/width)
        'X': ((cylinder_length/2, 0, 0), (axis_length - cone_height/2, 0, 0), (0, math.radians(90), 0)),    
        # Y-axis: Green cylinder along Y direction (front-back/depth)
        'Y': ((0, cylinder_length/2, 0), (0, axis_length - cone_height/2, 0), (math.radians(-90), 0, 0)),     
        # Z-axis: Blue cylinder along Z direction (up-down/height) 
        'Z': ((0, 0, cylinder_length/2), (0, 0, axis_length - cone_height/2), (0, 0, 0))                    
    }
    
    # Create only the visible axes
    for axis_name in visible_axes:
        cylinder_offset, cone_offset, rotation = all_axes_data[axis_name]
        
        # Add cylinder (shaft of the arrow)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=axis_thickness,
            depth=cylinder_length,
            location=(
                scene_center.x + cylinder_offset[0],
                scene_center.y + cylinder_offset[1], 
                scene_center.z + cylinder_offset[2]
            ),
            rotation=rotation
        )
        
        cylinder_obj = bpy.context.object
        cylinder_obj.name = f"Axis_{axis_name}_Cylinder"
        cylinder_obj.data.materials.append(materials[axis_name])
        
        # Add cone (arrowhead)
        bpy.ops.mesh.primitive_cone_add(
            radius1=cone_radius,
            depth=cone_height,
            location=(
                scene_center.x + cone_offset[0],
                scene_center.y + cone_offset[1],
                scene_center.z + cone_offset[2]
            ),
            rotation=rotation
        )
        
        cone_obj = bpy.context.object
        cone_obj.name = f"Axis_{axis_name}_Cone"
        cone_obj.data.materials.append(materials[axis_name])


def add_origin_marker(scene_center, marker_size=0.05):
    """
    Add a small sphere at the coordinate system origin for clear reference.
    scene_center: Vector
    """
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=marker_size,
        location=(scene_center.x, scene_center.y, scene_center.z)
    )
    
    origin_obj = bpy.context.object
    origin_obj.name = "Origin_Marker"
    
    # Create bright material for origin
    origin_mat = bpy.data.materials.new(name="Origin_Material")
    origin_mat.use_nodes = True
    bsdf = origin_mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs[0].default_value = (1.0, 1.0, 0.0, 1.0)  # Yellow
    bsdf.inputs[21].default_value = 2.0  # High emission
    origin_obj.data.materials.append(origin_mat)


def create_axes_material(visible_axes):
    # Create materials for each axis
    materials = {}
    colors = {
        'X': (1.0, 0.0, 0.0, 1.0),  # Red for X-axis
        'Y': (0.0, 1.0, 0.0, 1.0),  # Green for Y-axis
        'Z': (0.0, 0.0, 1.0, 1.0)   # Blue for Z-axis
    }
    
    for axis in visible_axes:
        color = colors[axis]
        mat = bpy.data.materials.new(name=f"Axis_{axis}_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs[0].default_value = color
        bsdf.inputs[21].default_value = 1.0
        materials[axis] = mat
    
    return materials


def create_text_label(scene_center, axis_length, visible_axes, materials,
                      label_offset_multiplier=1.15):
    """
        scene_center: Vector
    """
    text_objs = []
    for axis_name in visible_axes:
        # Add text label that faces the camera
        label_location = (
            scene_center.x + (axis_length * label_offset_multiplier if axis_name == 'X' else 0),
            scene_center.y + (axis_length * label_offset_multiplier if axis_name == 'Y' else 0),
            scene_center.z + (axis_length * label_offset_multiplier if axis_name == 'Z' else 0)
        )
        bpy.ops.object.text_add(location=label_location)
        text_obj = bpy.context.object
        text_obj.name = f"Axis_Label_{axis_name}"
        text_obj.data.body = axis_name
        text_obj.data.size = 0.2
        text_obj.data.materials.append(materials[axis_name])
        text_objs.append(text_obj)
    return text_objs


def rotate_text_labels_to_cam(text_objs, camera_pos, scene_center, visible_axes):

    camera_pos = Vector(camera_pos)
    scene_center = Vector(scene_center)
    for i in range(len(visible_axes)):
        axis_name = visible_axes[i]
        text_obj = text_objs[i]
        
        label_pos = Vector(text_obj.location)
        
        # Get camera direction (from this specific label to camera)
        cam_direction = (camera_pos - label_pos).normalized()
        
        # Determine which view we're in based on camera position relative to scene center
        scene_to_cam = camera_pos - scene_center
        
        # Determine the primary axis of the camera offset
        abs_x = abs(scene_to_cam.x)
        abs_y = abs(scene_to_cam.y) 
        abs_z = abs(scene_to_cam.z)
        
        # Calculate individual orientation for each axis label
        # We need different logic for each axis because they're at different positions
        
        if abs_z > abs_x and abs_z > abs_y:
            # Top/bottom view - camera is above or below (XY plane)
            if scene_to_cam.z > 0:
                # Top view (looking down) - all text should be readable from above
                if axis_name == 'X':
                    cam_right = mathutils.Vector((1, 0, 0))   
                    cam_up = mathutils.Vector((-1, 0, 0))
                elif axis_name == 'Y':
                    cam_right = mathutils.Vector((-1, 0, 0))
                    cam_up = mathutils.Vector((0, -1, 0))
                else:  # Z
                    cam_right = mathutils.Vector((1, 0, 0))
                    cam_up = mathutils.Vector((0, 1, 0))
            else:
                # Bottom view (looking up)
                if axis_name == 'X':
                    cam_right = mathutils.Vector((0, -1, 0))
                    cam_up = mathutils.Vector((-1, 0, 0))
                elif axis_name == 'Y':
                    cam_right = mathutils.Vector((1, 0, 0))
                    cam_up = mathutils.Vector((0, -1, 0))
                else:  # Z
                    cam_right = mathutils.Vector((-1, 0, 0))  
                    cam_up = mathutils.Vector((0, 1, 0))
                    
        elif abs_x > abs_y and abs_x > abs_z:
            # Side view - camera is to the left or right (YZ plane)
            if scene_to_cam.x > 0:
                # Right side view (looking from +X)
                if axis_name == 'X':
                    cam_right = mathutils.Vector((0, 0, 1))   
                    cam_up = mathutils.Vector((0, 1, 0))      
                elif axis_name == 'Y':
                    cam_right = mathutils.Vector((0, 1, 0)) 
                    cam_up = mathutils.Vector((0, 0, 1))  
                else:  # Z
                    cam_right = mathutils.Vector((0, -1, 0))
                    cam_up = mathutils.Vector((0, 0, -1))  
            else:
                # Left side view (looking from -X)
                if axis_name == 'X':
                    cam_right = mathutils.Vector((0, 0, -1)) 
                    cam_up = mathutils.Vector((0, 1, 0))   
                elif axis_name == 'Y':
                    cam_right = mathutils.Vector((0, 0, 1)) 
                    cam_up = mathutils.Vector((0, -1, 0))  
                else:  # Z
                    cam_right = mathutils.Vector((0, 1, 0)) 
                    cam_up = mathutils.Vector((0, 0, 1))
                    
        else:
            # Front/back view - camera is in front or behind (XZ plane)
            if scene_to_cam.y > 0:
                # Back view (looking from +Y)
                if axis_name == 'X':
                    cam_right = mathutils.Vector((-1, 0, 0))  
                    cam_up = mathutils.Vector((0, 0, 1))      
                elif axis_name == 'Y':
                    cam_right = mathutils.Vector((0, 0, 1))   
                    cam_up = mathutils.Vector((1, 0, 0))      
                else:  # Z
                    cam_right = mathutils.Vector((-1, 0, 0))  
                    cam_up = mathutils.Vector((0, 0, 1))      
            else:
                # Front view (looking from -Y)
                if axis_name == 'X':
                    cam_right = mathutils.Vector((1, 0, 0))   
                    cam_up = mathutils.Vector((0, 0, 1)) 
                elif axis_name == 'Y':
                    cam_right = mathutils.Vector((0, 0, 1))  
                    cam_up = mathutils.Vector((-1, 0, 0))  
                else:  # Z
                    cam_right = mathutils.Vector((1, 0, 0)) 
                    cam_up = mathutils.Vector((0, 0, 1))
        
        # Create rotation matrix for this specific label
        rot_matrix = mathutils.Matrix((
            cam_right,      # Text X axis
            cam_up,         # Text Y axis
            -cam_direction, # Text -Z axis (toward camera)
        )).transposed()
        
        # Apply the rotation
        text_obj.rotation_euler = rot_matrix.to_euler()
    return text_objs


def apply_text_rotation_by_axis(text_objs, visible_axes, rotation_angle):
    if visible_axes == ['X', 'Z']:
        view_name = 'front'
    elif visible_axes == ['Y', 'Z']:
        view_name = "side"
    else:
        view_name = "top"

    for i in range(len(visible_axes)):
        axis_name = visible_axes[i]
        text_obj = text_objs[i]
        # Apply opposite rotation to maintain same appearance
        opposite_angle = -rotation_angle
        
        # Different rotation logic based on which axis the text represents
        if view_name == 'front':
            # Front view (XZ plane) - camera rotates around Y-axis
            if axis_name == 'X':
                # X-axis label rotates around Y-axis
                text_obj.rotation_euler[1] -= math.radians(opposite_angle)
            elif axis_name == 'Z':
                # Z-axis label rotates around Y-axis
                text_obj.rotation_euler[1] -= math.radians(opposite_angle)
            # Y-axis is not visible in front view, so no rotation needed
                
        elif view_name == 'side':
            # Side view (YZ plane) - camera rotates around Y-axis
            if axis_name == 'Y':
                # Y-axis label rotates around Y-axis
                text_obj.rotation_euler[1] -= math.radians(opposite_angle)
            elif axis_name == 'Z':
                # Z-axis label rotates around Y-axis
                text_obj.rotation_euler[1] += math.radians(opposite_angle)
            # X-axis is not visible in side view, so no rotation needed
                
        elif view_name == 'top':
            # Top view (XY plane) - camera rotates around Z-axis
            if axis_name == 'X':
                # X-axis label rotates around Z-axis
                text_obj.rotation_euler[2] -= math.radians(opposite_angle)
            elif axis_name == 'Y':
                # Y-axis label rotates around Z-axis
                text_obj.rotation_euler[2] -= math.radians(opposite_angle)
            # Z-axis is not visible in top view, so no rotation needed


def create_scene_2D(scene_center, axis_length=1.0, axis_thickness=0.02, 
                    visible_axes=None, camera_position=None,
                    rotation_angle=None):
    if visible_axes is None:
        visible_axes = ['X', 'Y', 'Z']
    
    # We'll use the provided camera position or get current camera position as fallback
    if camera_position is None:
        camera = bpy.context.scene.camera
        if camera is None:
            camera_position = Vector(0, 0, 5)  # Default fallback position
        else:
            camera_position = camera.location
    
    # Convert to Vector for easier math
    camera_pos = mathutils.Vector(camera_position)
    
    add_origin_marker(scene_center)

    # Create materials for each axis
    materials = create_axes_material(visible_axes=visible_axes)
    
    add_coordinate_axes(scene_center, axis_length=axis_length, axis_thickness=axis_thickness, 
                        visible_axes=visible_axes, materials=materials)
    text_objs = create_text_label(scene_center, axis_length, visible_axes=visible_axes,
                                  materials=materials)
    updated_text_objs = rotate_text_labels_to_cam(text_objs, camera_pos=camera_pos, 
                                                  scene_center=scene_center, visible_axes=visible_axes)
    logger.info("text label rotated")
    if rotation_angle:
        apply_text_rotation_by_axis(updated_text_objs, visible_axes=visible_axes, 
                                    rotation_angle=rotation_angle)
        

def create_scene_3D(scene_center, axis_length=1.0, axis_thickness=0.02):
    visible_axes = ['X', 'Y', 'Z']
    # Create materials for each axis

    add_origin_marker(scene_center)

    materials = create_axes_material(visible_axes=visible_axes)
    
    add_coordinate_axes(scene_center, axis_length=axis_length, axis_thickness=axis_thickness, 
                        visible_axes=visible_axes, materials=materials)
    logger.info("Axes added")
    

def create_grid_material(color=(0.5, 0.5, 0.5), opacity=1.0):
    # Create material for grid lines if it doesn't exist
    grid_material_name = "Grid_Material"
    
    if grid_material_name not in bpy.data.materials:
        grid_material = bpy.data.materials.new(name=grid_material_name)
        grid_material.use_nodes = True
        
        # Clear existing nodes
        grid_material.node_tree.nodes.clear()
        
        # Create nodes for opaque colored material
        bsdf = grid_material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
        output = grid_material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
        
        # Set material properties
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)  # Set specified color
        bsdf.inputs['Roughness'].default_value = 0.1
        bsdf.inputs['Alpha'].default_value = opacity
        
        # Connect nodes
        grid_material.node_tree.links.new(bsdf.outputs[0], output.inputs[0])
        
        # Set blend method based on opacity
        if opacity < 1.0:
            grid_material.blend_method = 'BLEND'
        else:
            grid_material.blend_method = 'OPAQUE'
        
        grid_material.use_backface_culling = False
        
    else:
        grid_material = bpy.data.materials[grid_material_name]
        
        # Update color and opacity for existing material
        if grid_material.use_nodes:
            for node in grid_material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs['Base Color'].default_value = (*color, 1.0)
                    node.inputs['Alpha'].default_value = opacity
            
            # Update blend method based on opacity
            if opacity < 1.0:
                grid_material.blend_method = 'BLEND'
            else:
                grid_material.blend_method = 'OPAQUE'
    
    return grid_material


def create_grid_for_view(coords_center, view_name=None, grid_size=10, grid_spacing=1.0, 
                         camera_distance=5, opacity=0.3):
    grid_material = create_grid_material(opacity=opacity)
    
    # Calculate grid extent based on camera distance
    grid_extent = max(grid_size * grid_spacing, camera_distance * 1.5)
    
    # Create grid lines based on the view
    if view_name == 'front':
        # Front view: XZ plane - create lines parallel to X and Z axes
        create_grid_lines_xz_plane(coords_center, grid_extent, grid_spacing, grid_material)
    elif view_name == 'side':
        # Side view: YZ plane - create lines parallel to Y and Z axes  
        create_grid_lines_yz_plane(coords_center, grid_extent, grid_spacing, grid_material)
    elif view_name == 'top':
        # Top view: XY plane - create lines parallel to X and Y axes
        create_grid_lines_xy_plane(coords_center, grid_extent, grid_spacing, grid_material)
    else:
        # 3D grid
        # create_grid_lines_xz_plane(coords_center, grid_extent, grid_spacing, grid_material)
        # create_grid_lines_yz_plane(coords_center, grid_extent, grid_spacing, grid_material)
        create_grid_lines_xy_plane(coords_center, grid_extent, grid_spacing, grid_material)
        
    # bpy.ops.export_scene.gltf(
    #     filepath="./test_grid_scene",
    #     use_selection=False,
    #     export_apply=True,
    #     export_format='GLTF_SEPARATE'
    # )


def create_grid_lines_xz_plane(center, extent, spacing, material, save=False):
    """Create grid lines for XZ plane (front view)"""
    # Lines parallel to X-axis (varying Z)
    for i in range(-int(extent/spacing), int(extent/spacing) + 1):
        z_pos = center.z + i * spacing
        create_line(
            (center.x - extent, center.y, z_pos),
            (center.x + extent, center.y, z_pos),
            material, f"Grid_XZ_X_{i}"
        )
    
    # Lines parallel to Z-axis (varying X)
    for i in range(-int(extent/spacing), int(extent/spacing) + 1):
        x_pos = center.x + i * spacing
        create_line(
            (x_pos, center.y, center.z - extent),
            (x_pos, center.y, center.z + extent),
            material, f"Grid_XZ_Z_{i}"
        )
    if save:
        bpy.ops.export_scene.gltf(
            filepath="./test_grid_XZ",
            use_selection=False,
            export_apply=True,
            export_format='GLTF_SEPARATE'
        )


def create_grid_lines_yz_plane(center, extent, spacing, material, save=False):
    """Create grid lines for YZ plane (side view)"""
    # Lines parallel to Y-axis (varying Z)
    for i in range(-int(extent/spacing), int(extent/spacing) + 1):
        z_pos = center.z + i * spacing
        create_line(
            (center.x, center.y - extent, z_pos),
            (center.x, center.y + extent, z_pos),
            material, f"Grid_YZ_Y_{i}"
        )
    
    # Lines parallel to Z-axis (varying Y)
    for i in range(-int(extent/spacing), int(extent/spacing) + 1):
        y_pos = center.y + i * spacing
        create_line(
            (center.x, y_pos, center.z - extent),
            (center.x, y_pos, center.z + extent),
            material, f"Grid_YZ_Z_{i}"
        )
    if save:
        bpy.ops.export_scene.gltf(
            filepath="./test_grid_YZ",
            use_selection=False,
            export_apply=True,
            export_format='GLTF_SEPARATE'
        )


def create_grid_lines_xy_plane(center, extent, spacing, material, save=False):
    """Create grid lines for XY plane (top view)"""
    # Lines parallel to X-axis (varying Y)
    for i in range(-int(extent/spacing), int(extent/spacing) + 1):
        y_pos = center.y + i * spacing
        create_line(
            (center.x - extent, y_pos, center.z),
            (center.x + extent, y_pos, center.z),
            material, f"Grid_XY_X_{i}"
        )
    
    # Lines parallel to Y-axis (varying X)
    for i in range(-int(extent/spacing), int(extent/spacing) + 1):
        x_pos = center.x + i * spacing
        create_line(
            (x_pos, center.y - extent, center.z),
            (x_pos, center.y + extent, center.z),
            material, f"Grid_XY_Y_{i}"
        )
    if save:
        bpy.ops.export_scene.gltf(
            filepath="./test_grid_XY",
            use_selection=False,
            export_apply=True,
            export_format='GLTF_SEPARATE'
        )


def create_line(start_pos, end_pos, material, name):
    """
    Create a line object as a thin cylinder between two points
    
    :param start_pos: Starting position (x, y, z)
    :param end_pos: Ending position (x, y, z)
    :param material: Material to apply to the line
    :param name: Name for the line object
    """

    logger.info(f"Creating line '{name}' from {start_pos} to {end_pos}")

    try:
        # Calculate line properties
        start = Vector(start_pos)
        end = Vector(end_pos)
        direction = end - start
        length = direction.length
        center = (start + end) / 2
        
        logger.info(f"Line length: {length:.3f}, center: {center}")
        
        if length < 0.001:  # Very short line
            logger.warning(f"Line '{name}' is very short ({length:.6f}) - might not be visible")
        
        # Create cylinder at origin first
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.01,  # Thin cylinder radius
            depth=length,
            location=(0, 0, 0),  # Create at origin
            vertices=8  # 8-sided cylinder
        )
        
        # Get the created object (it becomes the active object)
        line_obj = bpy.context.active_object
        line_obj.name = name
        
        logger.info(f"Created cylinder object: {line_obj.name} at origin")
        
        # Align the cylinder with the line direction
        if direction.length > 0:
            direction.normalize()
            # Default cylinder is aligned with Z-axis (0,0,1)
            z_axis = Vector((0, 0, 1))
            
            logger.debug(f"Direction vector: {direction}, Z-axis: {z_axis}")
            
            # Calculate rotation needed to align Z-axis with our direction
            dot_product = direction.dot(z_axis)
            logger.debug(f"Dot product: {dot_product:.3f}")
            
            if abs(dot_product) < 0.999:  # Not already aligned
                rotation_axis = z_axis.cross(direction)
                rotation_angle = z_axis.angle(direction)
                logger.info(f"Rotating by {rotation_angle:.3f} radians around axis {rotation_axis}")
                
                # Apply rotation around origin
                rotation_matrix = Matrix.Rotation(rotation_angle, 4, rotation_axis)
                line_obj.matrix_world = rotation_matrix
                
            elif dot_product < 0:  # Pointing in opposite direction
                logger.info("Flipping cylinder 180 degrees")
                line_obj.rotation_euler = (3.14159, 0, 0)  # 180 degrees around X
            else:
                logger.info("Cylinder already aligned with direction")
        else:
            logger.warning(f"Zero-length direction vector for line '{name}'")
        
        # NOW move the cylinder to the correct center position
        # This ensures the center is correct after rotation
        line_obj.location = center
        logger.info(f"Moved cylinder to final center position: {center}")
        
        # Apply material
        if material:
            if line_obj.data.materials:
                line_obj.data.materials[0] = material
                logger.info(f"Replaced existing material with {material.name}")
            else:
                line_obj.data.materials.append(material)
                logger.info(f"Applied material {material.name}")
        else:
            logger.warning(f"No material provided for line '{name}'")
        
        logger.info(f"Successfully created line '{name}' with final location: {line_obj.location}")
        logger.info(f"Final rotation: {line_obj.rotation_euler}")
        
        return line_obj
        
    except Exception as e:
        logger.error(f"Error creating line '{name}': {str(e)}")
        logger.error(f"Start pos: {start_pos}, End pos: {end_pos}")
        raise e
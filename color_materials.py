from typing import Dict, List, Tuple
import random
import bpy


def generate_color_map(objects_list: List[str], seed: int = None) -> Dict[str, Tuple[float, float, float]]:
    """
    Generates a color map by randomly assigning predefined colors to objects.
    
    Args:
        objects_list: List of object names/types to generate colors for
        seed: Random seed for reproducible colors (optional)
    
    Returns:
        Dict mapping object names to RGB tuples (values 0.0-1.0)
    """
    if seed is not None:
        random.seed(seed)
    
    # Predefined colors (avoiding red, green, blue, yellow used for axes/origin)
    available_colors = {
        'purple': (0.6, 0.2, 0.8),
        'orange': (1.0, 0.5, 0.0),
        'pink': (1.0, 0.4, 0.7),
        'cyan': (0.0, 0.8, 0.8),
        'magenta': (0.8, 0.0, 0.8),
        'lime': (0.5, 1.0, 0.0),
        'brown': (0.6, 0.3, 0.1),
        'teal': (0.0, 0.5, 0.5),
        'indigo': (0.3, 0.0, 0.5),
        'coral': (1.0, 0.5, 0.3),
        'lavender': (0.9, 0.6, 1.0),
        'olive': (0.5, 0.5, 0.0),
        'navy': (0.0, 0.0, 0.5),
        'maroon': (0.5, 0.0, 0.0),
        'turquoise': (0.3, 0.8, 0.8),
    }
    
    color_names = list(available_colors.keys())
    
    # Shuffle colors for random assignment
    random.shuffle(color_names)
    
    color_map = {}
    for i, obj_name in enumerate(objects_list):
        # Cycle through colors if we have more objects than colors
        color_name = color_names[i % len(color_names)]
        color_map[obj_name] = available_colors[color_name]
    
    return color_map


def get_color_name_from_rgb(rgb_tuple):
    # Predefined color names mapping (should match your color generation function)
    color_names = {
        (0.6, 0.2, 0.8): 'purple',
        (1.0, 0.5, 0.0): 'orange', 
        (1.0, 0.4, 0.7): 'pink',
        (0.0, 0.8, 0.8): 'cyan',
        (0.8, 0.0, 0.8): 'magenta',
        (0.5, 1.0, 0.0): 'lime',
        (0.6, 0.3, 0.1): 'brown',
        (0.0, 0.5, 0.5): 'teal',
        (0.3, 0.0, 0.5): 'indigo',
        (1.0, 0.5, 0.3): 'coral',
        (0.9, 0.6, 1.0): 'lavender',
        (0.5, 0.5, 0.0): 'olive',
        (0.0, 0.0, 0.5): 'navy',
        (0.5, 0.0, 0.0): 'maroon',
        (0.3, 0.8, 0.8): 'turquoise',
    }
    
    # Find closest color match (simple exact match first, then closest)
    if rgb_tuple in color_names:
        return color_names[rgb_tuple]
    
    # If no exact match, find closest RGB values
    min_distance = float('inf')
    closest_color = 'colored'
    
    for color_rgb, color_name in color_names.items():
        # Calculate Euclidean distance in RGB space
        distance = sum((a - b) ** 2 for a, b in zip(rgb_tuple, color_rgb)) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    
    return closest_color


def create_colored_material(part_name, color_map, opacity=0.5):
    """
    Creates or retrieves a colored material for a specific part with opacity.
    
    Args:
        part_name: Name of the part
        color_map: Dictionary mapping part names to RGB colors
        opacity: float - Alpha/transparency value (0.0-1.0)
                0.0 = fully transparent, 1.0 = fully opaque
    
    Returns:
        Blender material object
    """
    # Generate material name based on part name and opacity
    mat_name = f"Material_{part_name}_{opacity:.2f}"
    
    # Get color from mapping, default to gray if not found
    if part_name in color_map:
        color = color_map[part_name]
    else:
        color = (0.5, 0.5, 0.5)  # Default gray
    
    # Check if material already exists
    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
    else:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        # Set up the material color and opacity
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            # Convert RGB to RGBA if needed
            if len(color) == 3:
                rgba_color = (*color, 1.0)
            else:
                rgba_color = color
            bsdf.inputs["Base Color"].default_value = rgba_color
            bsdf.inputs["Alpha"].default_value = opacity
            
            # Optional: Make materials slightly more vibrant
            bsdf.inputs["Metallic"].default_value = 0.1
            bsdf.inputs["Roughness"].default_value = 0.3
        
        # Handle transparency if opacity < 1.0
        if opacity < 1.0:
            mat.blend_method = 'BLEND'
            mat.use_backface_culling = False
    
    return mat
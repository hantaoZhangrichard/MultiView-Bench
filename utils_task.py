import math
import random
import os
import logging

logger = logging.getLogger("utils_task")


def generate_random_axes(degree_of_freedom):
    if degree_of_freedom not in [1, 2, 3]:
        raise ValueError(f"Degree of freedom must be 1, 2, or 3. Got: {degree_of_freedom}")
    
    all_axes = ["X", "Y", "Z"]
    
    # Randomly sample the specified number of axes without replacement
    selected_axes = random.sample(all_axes, degree_of_freedom)
    
    # return selected_axes
    return selected_axes


def generate_random_positions(objects, axes, center=(0, 0, 0), radius=2.0, 
                              min_separation=1.4, max_attempts=1000, threshold=0.3):
    positioned_objects = {}
    placed_positions = []
    
    # Normalize axes input to uppercase
    axes = [axis.upper() for axis in axes]
    
    for obj in objects:
        attempts = 0
        while attempts < max_attempts:
            # Initialize position at center
            x, y, z = center
            
            if len(axes) == 3 and set(axes) == {"X", "Y", "Z"}:
                # Full 3D sphere surface
                azimuth = random.uniform(0, 2 * math.pi)
                elevation = math.acos(random.uniform(-1, 1))
                
                x = center[0] + radius * math.sin(elevation) * math.cos(azimuth)
                y = center[1] + radius * math.sin(elevation) * math.sin(azimuth)
                z = center[2] + radius * math.cos(elevation)
                
            elif len(axes) == 2:
                # 2D circle on a plane
                angle = random.uniform(0, 2 * math.pi)
                
                if set(axes) == {"X", "Y"}:
                    # XY plane (Z = center[2])
                    x = center[0] + radius * math.cos(angle)
                    y = center[1] + radius * math.sin(angle)
                    z = center[2]
                elif set(axes) == {"X", "Z"}:
                    # XZ plane (Y = center[1])
                    x = center[0] + radius * math.cos(angle)
                    y = center[1]
                    z = center[2] + radius * math.sin(angle)
                elif set(axes) == {"Y", "Z"}:
                    # YZ plane (X = center[0])
                    x = center[0]
                    y = center[1] + radius * math.cos(angle)
                    z = center[2] + radius * math.sin(angle)
                else:
                    raise ValueError(f"Invalid 2-axis combination: {axes}")
                    
            elif len(axes) == 1:
                # 1D line along a single axis
                # Generate random point on line segment of length 2*radius
                offset = random.uniform(-radius, radius)
                
                if axes[0] == "X":
                    x = center[0] + offset
                    y = center[1]
                    z = center[2]
                elif axes[0] == "Y":
                    x = center[0]
                    y = center[1] + offset
                    z = center[2]
                elif axes[0] == "Z":
                    x = center[0]
                    y = center[1]
                    z = center[2] + offset
                else:
                    raise ValueError(f"Invalid axis: {axes[0]}")
            else:
                raise ValueError(f"Invalid number of axes: {len(axes)}. Must be 1, 2, or 3.")
            
            # Apply threshold snapping - set small deviations to zero
            if abs(x - center[0]) < threshold:
                x = center[0]
            if abs(y - center[1]) < threshold:
                y = center[1]
            if abs(z - center[2]) < threshold:
                z = center[2]
            
            new_position = (x, y, z)
            
            # Check if this position is far enough from all existing objects
            valid_position = True
            for existing_pos in placed_positions:
                distance_between = math.sqrt(
                    (x - existing_pos[0])**2 + 
                    (y - existing_pos[1])**2 + 
                    (z - existing_pos[2])**2
                )
                if distance_between < min_separation:
                    valid_position = False
                    break
            
            if valid_position:
                positioned_objects[obj] = new_position
                placed_positions.append(new_position)
                break
            
            attempts += 1
        
        # If we couldn't place the object after max_attempts, place it anyway with a warning
        if obj not in positioned_objects:
            logger.info(f"Warning: Could not find non-intersecting position for {obj} after {max_attempts} attempts")
            positioned_objects[obj] = new_position
            placed_positions.append(new_position)
    
    return positioned_objects


def sample_random_shapes(num_shapes=2, available_shapes=None):
    if available_shapes is None:
        available_shapes = ['cube', 'sphere', 'cone', 'cylinder']
    
    # Ensure we don't sample more shapes than available
    num_shapes = min(num_shapes, len(available_shapes))
    
    # Sample without replacement to ensure unique shapes
    sampled_shapes = random.sample(available_shapes, num_shapes)
    
    return sampled_shapes


def sample_random_objects(gltf_base_dir, categories, num_objects=2):
    """
    Sample one object ID randomly from each category in the gltf_base_dir.
    
    Args:
        gltf_base_dir: str - Base directory containing GLTF files
        categories: list - List of category codes to filter by (e.g., [25, 30, 45])
        num_objects: int - Number of objects to sample (must equal len(categories))
    
    Returns:
        list - List of sampled object IDs, one from each category (e.g., ["25_325", "30_102", "45_789"])
    
    Raises:
        ValueError: if num_objects != len(categories)
    """
    # Validate that num_objects matches the number of categories
    if num_objects != len(categories):
        raise ValueError(f"Number of objects ({num_objects}) must equal the number of categories ({len(categories)})")
    
    # Convert categories to strings for comparison
    category_strs = [str(cat) for cat in categories]
    
    # Find all GLTF files in the directory
    all_files = []
    try:
        for filename in os.listdir(gltf_base_dir):
            if filename.endswith('.gltf'):
                all_files.append(filename)
    except FileNotFoundError:
        logger.error(f"Directory not found: {gltf_base_dir}")
        return []
    except Exception as e:
        logger.error(f"Error reading directory {gltf_base_dir}: {str(e)}")
        return []
    
    # Group files by category codes
    objects_by_category = {}
    for filename in all_files:
        # Remove the .gltf extension to get object_id
        object_id = filename.replace('.gltf', '')
        
        # Check if object_id follows the expected format (category_id)
        if '_' in object_id:
            category_code = object_id.split('_')[0]
            if category_code in category_strs:
                if category_code not in objects_by_category:
                    objects_by_category[category_code] = []
                objects_by_category[category_code].append(object_id)
    
    # Check if we have objects for all requested categories
    missing_categories = []
    for category_str in category_strs:
        if category_str not in objects_by_category or not objects_by_category[category_str]:
            missing_categories.append(category_str)
    
    if missing_categories:
        logger.warning(f"No objects found for categories {missing_categories} in {gltf_base_dir}")
        return []
    
    # Sample one object from each category
    sampled_objects = []
    for category_str in category_strs:
        available_objects = objects_by_category[category_str]
        sampled_object = random.choice(available_objects)
        sampled_objects.append(sampled_object)
    
    logger.info(f"Sampled {len(sampled_objects)} objects (one from each category {categories}): {sampled_objects}")
    
    return sampled_objects
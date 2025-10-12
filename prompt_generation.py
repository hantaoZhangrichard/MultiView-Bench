import random
import logging
from color_materials import get_color_name_from_rgb

logger = logging.getLogger("prompt_generation")


def get_axis_sign(value, threshold=0.3):
    """Get the sign of axis displacement with threshold for zero"""
    if abs(value) < threshold:
        return "0"
    return "+" if value > 0 else "-"


def get_object_name(object_id):
    prefix_map = {
        '00': 'airplane', 
        '01': 'bag', 
        '02': 'basket', 
        '03': 'bbq_grill', 
        '04': 'bed', 
        '05': 'bench', 
        '06': 'bicycle', 
        '07': 'bird_house', 
        '08': 'boat', 
        '09': 'cabinet', 
        '0a': 'candle_holder', 
        '0b': 'car', 
        '0c': 'chair', 
        '0d': 'clock', 
        '0e': 'coat_rack', 
        '0f': 'curtain', 
        '10': 'dishwasher', 
        '11': 'dresser', 
        '12': 'fan', 
        '13': 'faucet', 
        '14': 'garbage_bin', 
        '15': 'gazebo', 
        '16': 'jug', 
        '17': 'ladder', 
        '18': 'lamp', 
        '19': 'love_seat', 
        '1a': 'ottoman', 
        '1b': 'parasol', 
        '1c': 'planter', 
        '1d': 'shelf', 
        '1e': 'shower', 
        '1f': 'sinks', 
        '20': 'skateboard', 
        '21': 'sofa', 
        '22': 'sports_table', 
        '23': 'stool', 
        '24': 'sun_lounger', 
        '25': 'table', 
        '26': 'toilet', 
        '27': 'tray', 
        '28': 'trolley', 
        '29': 'vase'}
    if "_" in object_id:  # Ensure the file has an underscore
        prefix = object_id.split("_")[0]
    return prefix_map[prefix]


def replace_ids_by_names(obj_dict, id=None):
    new_dict = {}
    for obj_id, value in obj_dict.items():
        obj_name = get_object_name(obj_id)
        new_dict[obj_name] = value
    if id:
        obj_name = get_object_name(id)
        return new_dict, obj_name
    else:
        return new_dict, None


def get_objects_metadata_for_prompt(experiment_config, real_world=False):
    central_obj = experiment_config['central_object']
    central_pos = experiment_config['central_position']
    all_objects = experiment_config['objects']
    central_object_name = central_obj['type']

    if real_world:
        all_objects, central_object_name = replace_ids_by_names(all_objects, central_obj['type'])
    
    # Get all objects except the central object
    other_objects = {name: pos for name, pos in all_objects.items() 
                    if name != central_object_name}
    
    # Randomly sample one object from the remaining objects
    sampled_obj_name = random.choice(list(other_objects.keys()))
    sampled_obj_pos = other_objects[sampled_obj_name]
    
    # Calculate relative vector (sampled_object_position - central_position)
    relative_vector = {
        'x': sampled_obj_pos[0] - central_pos[0],
        'y': sampled_obj_pos[1] - central_pos[1],
        'z': sampled_obj_pos[2] - central_pos[2]
    }
    
    target_object_name = sampled_obj_name

    return central_object_name, target_object_name, relative_vector


def generate_color_description(color_map, real_world=False):
    # Create color description if color mapping is enabled
    color_description = ""
    if real_world:
        color_map, _ = replace_ids_by_names(color_map, id=None)
    if color_map:
        # Create a string describing each object's color
        color_descriptions = []
        for obj_type, color_rgb in color_map.items():
            color_name = get_color_name_from_rgb(color_rgb)
            color_descriptions.append(f"- {obj_type}: {color_name}")
        
        color_list = "\n".join(color_descriptions)
        color_description = f"""
OBJECT COLORS:
{color_list}
- Use these colors along with shapes to identify the objects mentioned in the task
"""
    
    return color_description


def generate_vlm_test_question(experiment_config, color=False, real_world=False):
    
    central_object_name, target_object_name, relative_vector = get_objects_metadata_for_prompt(experiment_config, real_world)

    logger.info(f"Object names are: {central_object_name}, {target_object_name}")

    if color:
        color_map = experiment_config.get('color_map', {})
        color_description = generate_color_description(color_map, real_world=real_world)
    else:
        color_description = ""

    # Generate question with clear, structured prompt
    question = f"""Look at this 3D scene carefully from different viewpoints. You can see several geometric objects and coordinate axes.

COORDINATE SYSTEM:
- X-axis: RED rod, pointing to positive X direction
- Y-axis: GREEN rod, pointing to positive Y direction
- Z-axis: BLUE rod, pointing to position Z direction
- Origin (0,0,0): YELLOW sphere, located at the center of the {central_object_name}{color_description}

TASK:
Determine the relative position of the {target_object_name} compared to the {central_object_name} in terms of their geometric centers.

INSTRUCTIONS:
1. Look at where the {target_object_name} is positioned relative to the {central_object_name}
2. For each axis, determine if the {target_object_name} is in the positive (+) or negative (-) direction using the coordinate system shown in the images.
3. If objects appear at approximately the same level on an axis, use (0)

ANSWER FORMAT:
Respond with exactly this format: <answer>(±X, ±Y, ±Z)</answer>
Examples: <answer>(+X, -Y, +Z)</answer> or <answer>(-X, 0Y, -Z)</answer> or <answer>(0X, +Y, 0Z)</answer>

What is the relative position of the {target_object_name} to the {central_object_name}?"""
    
    expected_answer = f"({get_axis_sign(relative_vector['x'])}X, " \
                     f"{get_axis_sign(relative_vector['y'])}Y, " \
                     f"{get_axis_sign(relative_vector['z'])}Z)"
    
    return {
        "question": question,
        "expected_answer": expected_answer,
        "target_object_clean": target_object_name,
        "central_object_clean": central_object_name,
        "ground_truth_vector": relative_vector
    }


def generate_vlm_test_questions_multiagent(experiment_config, color=False, real_world=False):
    central_object_name, target_object_name, relative_vector = get_objects_metadata_for_prompt(experiment_config, real_world)
    
    # Define the three views and their visible axes
    views = {
        'front': {
            'name': 'Front View (XZ plane)',
            'visible_axes': ['X', 'Z'],
            'axis_descriptions': [
                "X-axis: RED rod, pointing to positive X direction",
                "Z-axis: BLUE rod, pointing to positive Z direction"
            ],
            'viewing_direction': 'looking along the Y-axis'
        },
        'side': {
            'name': 'Side View (YZ plane)', 
            'visible_axes': ['Y', 'Z'],
            'axis_descriptions': [
                "Y-axis: GREEN rod, pointing to positive Y direction",
                "Z-axis: BLUE rod, pointing to positive Z direction"
            ],
            'viewing_direction': 'looking along the X-axis'
        },
        'top': {
            'name': 'Top View (XY plane)',
            'visible_axes': ['X', 'Y'],
            'axis_descriptions': [
                "X-axis: RED rod, pointing to positive X direction",
                "Y-axis: GREEN rod, pointing to positive Y direction"
            ],
            'viewing_direction': 'looking along the Z-axis from above'
        }
    }

    if color:
        color_map = experiment_config.get('color_map', {})
        color_description = generate_color_description(color_map)
    else:
        color_description = ""
    
    # Generate questions for each view
    questions = {}
    
    for view_key, view_info in views.items():
        # Create axis descriptions string
        axis_desc = "\n- ".join([""] + view_info['axis_descriptions'])
        
        # Create the question for this view
        question = f"""Look at this {view_info['name']} carefully. You can see several geometric objects and coordinate axes.

VIEW DESCRIPTION:
This is the {view_info['name']}, {view_info['viewing_direction']}.

COORDINATE SYSTEM:{axis_desc}
- Origin (0,0,0): YELLOW sphere, located at the center of the {central_object_name}{color_description}

TASK:
Determine the relative position of the {target_object_name} compared to the {central_object_name} in terms of their geometric centers, focusing only on the {' and '.join(view_info['visible_axes'])} axes visible in this view.

INSTRUCTIONS:
1. Look at where the {target_object_name} is positioned relative to the {central_object_name}
2. For each visible axis ({', '.join(view_info['visible_axes'])}), determine if the {target_object_name} is in the positive (+) or negative (-) direction using the coordinate system shown in the image.
3. If objects appear at approximately the same level on an axis, use (0)

ANSWER FORMAT:
Respond with exactly this format for the {' and '.join(view_info['visible_axes'])} axes: <answer>(±{view_info['visible_axes'][0]}, ±{view_info['visible_axes'][1]})</answer>
Examples: <answer>(+{view_info['visible_axes'][0]}, -{view_info['visible_axes'][1]})</answer> or <answer>(0{view_info['visible_axes'][0]}, +{view_info['visible_axes'][1]})</answer>

What is the relative position of the {target_object_name} to the {central_object_name} in the {' and '.join(view_info['visible_axes'])} axes?"""

        # Generate expected answer for this view's visible axes
        axis_values = {
            'X': relative_vector['x'],
            'Y': relative_vector['y'], 
            'Z': relative_vector['z']
        }
        
        axis1, axis2 = view_info['visible_axes']
        expected_answer = f"({get_axis_sign(axis_values[axis1])}{axis1}, " \
                         f"{get_axis_sign(axis_values[axis2])}{axis2})"
        
        questions[view_key] = {
            "question": question,
            "expected_answer": expected_answer,
            "visible_axes": view_info['visible_axes'],
            "view_name": view_info['name']
        }
    
    # Common metadata for all views
    common_metadata = {
        "target_object_clean": target_object_name,
        "central_object_clean": central_object_name,
        "ground_truth_vector": relative_vector,
        "color_enabled": color
    }
    
    return {
        "questions": questions,
        "metadata": common_metadata,
        "full_expected_answer": f"({get_axis_sign(relative_vector['x'])}X, " \
                               f"{get_axis_sign(relative_vector['y'])}Y, " \
                               f"{get_axis_sign(relative_vector['z'])}Z)"
    }


def generate_vlm_test_question_visibility(experiment_config, color=False, real_world=False):
    
    central_object_name, target_object_name, relative_vector = get_objects_metadata_for_prompt(experiment_config, real_world)

    logger.info(f"Object names are: {central_object_name}, {target_object_name}")

    if color:
        color_map = experiment_config.get('color_map', {})
        color_description = generate_color_description(color_map, real_world=real_world)
    else:
        color_description = ""

    # Generate question with clear, structured prompt
    question = f"""Look at this 3D scene carefully from different viewpoints. You can see several geometric objects and coordinate axes.

COORDINATE SYSTEM:
- X-axis: RED rod, pointing to positive X direction
- Y-axis: GREEN rod, pointing to positive Y direction
- Z-axis: BLUE rod, pointing to position Z direction
- Origin (0,0,0): YELLOW sphere, located at the center of the {central_object_name}{color_description}

TASK:
Determine the relative position of the {target_object_name} compared to the {central_object_name} in terms of their geometric centers.

INSTRUCTIONS:
1. Look at where the {target_object_name} is positioned relative to the {central_object_name}
2. Determine which axes are clearly visible in the image. 
3. For each visible axis, determine if the {target_object_name} is in the positive (+) or negative (-) direction using the coordinate system shown in the images.
4. If objects appear at approximately the same level on an axis, use (0)

ANSWER FORMAT:
Respond with exactly this format: <answer>(±X, ±Y, ±Z)</answer>
You only need to include directions for those visible axes.
Examples: <answer>(+X, -Y, +Z)</answer> or <answer>(-X, 0Y, -Z)</answer> or <answer>(0X, +Y, 0Z)</answer>

What is the relative position of the {target_object_name} to the {central_object_name}?"""
    
    expected_answer = f"({get_axis_sign(relative_vector['x'])}X, " \
                     f"{get_axis_sign(relative_vector['y'])}Y, " \
                     f"{get_axis_sign(relative_vector['z'])}Z)"
    
    return {
        "question": question,
        "expected_answer": expected_answer,
        "target_object_clean": target_object_name,
        "central_object_clean": central_object_name,
        "ground_truth_vector": relative_vector
    }
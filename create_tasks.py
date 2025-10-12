import os
import logging
import random
from datetime import datetime
import csv
import time
from mathutils import Vector
from utils_task import sample_random_objects, sample_random_shapes
from utils_task import generate_random_axes, generate_random_positions
from color_materials import generate_color_map
from bpy_execution import execute_blender_tasks_direct_sequential
from prompt_generation import generate_vlm_test_question, generate_vlm_test_questions_multiagent
from render import render_scene_sequential


logger = logging.getLogger("create_tasks")


def create_experiment(output_dir, num_shapes=2, exp_size=5, 
                      dof=3, radius=1.4,
                      save_csv=True, csv_filename=None, multi_agent=False,
                      colors=True, scale=(0.5, 0.5, 0.5), opacity=0.3, 
                      real_world=True, categories=None,
                      gltf_base_dir=None, seed=None):
    # Set random seed if provided
    if seed is not None:
        random.seed(seed)
        logger.info(f"Random seed set to: {seed}")
    
    blender_tasks = []
    qa_tuples = []
    
    for i in range(exp_size):
        task_id = f"task_{i+1}"
        output_path = os.path.join(output_dir, f"{task_id}.gltf")
        if real_world:
            sampled_shapes = sample_random_objects(gltf_base_dir=gltf_base_dir, 
                                                   categories=categories, 
                                                   num_objects=num_shapes)
        else:
            sampled_shapes = sample_random_shapes(num_shapes=num_shapes)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Choose central object (where coordinate axes will be placed)
        central_object_type = random.choice(sampled_shapes)
        other_object_types = [shape for shape in sampled_shapes if shape != central_object_type]
        
        # Position central object at origin
        central_position = (0, 0, 0)
        
        dof_axes = generate_random_axes(degree_of_freedom=dof)

        # Generate random positions for other objects
        objects_dict = generate_random_positions(
            objects=other_object_types,
            axes=dof_axes,
            center=central_position,
            radius=radius,
        )
        logger.info(objects_dict)
        # Add central object to the objects dictionary
        objects_dict[f"{central_object_type}"] = central_position
        
        if colors:
            color_map = generate_color_map(objects_list=objects_dict.keys(), seed=seed)
        else:
            color_map = None
        logger.info(color_map)

        # Create blender task tuple
        blender_task = (objects_dict, output_path, task_id, color_map, scale, opacity)
        blender_tasks.append(blender_task)

        logger.info(blender_task)
        
        # Create experiment configuration for VLM question generation
        experiment_config = {
            'central_object': {
                'name': f"{central_object_type}_central",
                'type': central_object_type
            },
            'central_position': central_position,
            'objects': objects_dict,
            'task_id': task_id,
            'color_map': color_map
        }
        
        if multi_agent:
            # Generate multi-agent VLM test questions
            vlm_question_data = generate_vlm_test_questions_multiagent(experiment_config, 
                                                                       color=colors, real_world=real_world)
            
            # Create multi-agent Q&A structure
            qa_tuple = {
                'task_id': task_id,
                'front_view': {
                    'question': vlm_question_data["questions"]["front"]["question"],
                    'answer': vlm_question_data["questions"]["front"]["expected_answer"],
                    'visible_axes': vlm_question_data["questions"]["front"]["visible_axes"]
                },
                'side_view': {
                    'question': vlm_question_data["questions"]["side"]["question"],
                    'answer': vlm_question_data["questions"]["side"]["expected_answer"],
                    'visible_axes': vlm_question_data["questions"]["side"]["visible_axes"]
                },
                'top_view': {
                    'question': vlm_question_data["questions"]["top"]["question"],
                    'answer': vlm_question_data["questions"]["top"]["expected_answer"],
                    'visible_axes': vlm_question_data["questions"]["top"]["visible_axes"]
                },
                'metadata': vlm_question_data["metadata"],
                'full_expected_answer': vlm_question_data["full_expected_answer"]
            }
        else:
            # Generate single-agent VLM test question
            vlm_question_data = generate_vlm_test_question(experiment_config,
                                                           color=colors, real_world=real_world)
            
            # Create simple (question, answer) tuple
            qa_tuple = (
                vlm_question_data["question"],
                vlm_question_data["expected_answer"]
            )
        
        qa_tuples.append(qa_tuple)
    
    # Save Q&A pairs to CSV file
    csv_path = None
    if save_csv:
        if multi_agent:
            csv_path = save_multiagent_qa_tuples_to_csv(qa_tuples, output_dir, csv_filename)
        else:
            csv_path = save_qa_tuples_to_csv(qa_tuples, output_dir, csv_filename)
    
    return blender_tasks, qa_tuples, csv_path


def save_multiagent_qa_tuples_to_csv(qa_tuples, output_dir, csv_filename=None):
    
    if csv_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"multiagent_qa_pairs_{timestamp}.csv"
    
    csv_path = os.path.join(output_dir, csv_filename)
    
    # Define simplified CSV headers
    headers = [
        'task_id',
        'front_question',
        'side_question', 
        'top_question',
        'full_expected_answer'
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for qa_dict in qa_tuples:
            row = {
                'task_id': qa_dict['task_id'],
                'front_question': qa_dict['front_view']['question'],
                'side_question': qa_dict['side_view']['question'],
                'top_question': qa_dict['top_view']['question'],
                'full_expected_answer': qa_dict['full_expected_answer']
            }
            writer.writerow(row)
    
    logger.info(f"Multi-agent Q&A pairs saved to: {csv_path}")
    return csv_path


def prepare_experiment(blender_tasks, image_base_dir, show_coords=True, show_grid=True, mode='3D',
                       rotation_angle=0, 
                       real_world=True, gltf_base_dir=None,
                       vg_mode='circle', **view_kwargs):
    experiment_start_time = time.time()
    
    # Execute blender tasks
    blender_start_time = time.time()
    
    results = execute_blender_tasks_direct_sequential(blender_tasks=blender_tasks, real_world=real_world,
                                                      gltf_base_dir=gltf_base_dir)
    
    blender_end_time = time.time()
    blender_duration = blender_end_time - blender_start_time
    
    # Prepare render tasks
    render_prep_start_time = time.time()
    
    render_tasks = []
    for (_, output_path, task_id, _, _, _) in blender_tasks:
        image_output_path = f"{image_base_dir}/{task_id}"
        os.makedirs(image_output_path, exist_ok=True)
        render_tasks.append((image_output_path, task_id, output_path))
    
    render_prep_end_time = time.time()
    render_prep_duration = render_prep_end_time - render_prep_start_time
    
    total_render_tasks = len(render_tasks)
    
    # Execute render tasks
    render_start_time = time.time()
    
    coords_center = Vector((0, 0, 0))
    render_results = render_scene_sequential(render_tasks, show_coords=show_coords, show_grid=show_grid, 
                                             coords_center=coords_center, mode=mode, 
                                             rotation_angle=rotation_angle,
                                             vg_mode=vg_mode, **view_kwargs)
    
    render_end_time = time.time()
    render_duration = render_end_time - render_start_time
    
    # Calculate total time
    experiment_end_time = time.time()
    total_duration = experiment_end_time - experiment_start_time
    
    # Return comprehensive results with timing information
    return {
        'blender_results': results,
        'render_results': render_results,
        'timing': {
            'total_duration': total_duration,
            'blender_duration': blender_duration,
            'render_prep_duration': render_prep_duration,
            'render_duration': render_duration,
            'tasks_processed': len(blender_tasks),
            'renders_completed': total_render_tasks,
            'avg_time_per_task': total_duration / len(blender_tasks),
            'avg_time_per_render': render_duration / total_render_tasks if total_render_tasks > 0 else 0
        },
        'task_breakdown': {
            'num_tasks': len(blender_tasks),
            'total_renders': total_render_tasks
        }
    }


def save_qa_tuples_to_csv(qa_tuples, output_dir, csv_filename=None):
    # Generate filename if not provided
    if csv_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"qa_pairs_{timestamp}.csv"
    
    # Ensure CSV extension
    if not csv_filename.endswith('.csv'):
        csv_filename += '.csv'
    
    csv_path = os.path.join(output_dir, csv_filename)
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Task_ID', 'Question', 'Answer'])
            
            # Write Q&A pairs with task IDs
            for i, (question, answer) in enumerate(qa_tuples, 1):
                task_id = f"task_{i}"
                writer.writerow([task_id, question, answer])
        
        logger.info(f"✓ Q&A pairs saved to: {csv_path}")
        logger.info(f"  Total pairs: {len(qa_tuples)}")
        return csv_path
        
    except Exception as e:
        logger.info(f"Error saving CSV file: {str(e)}")
        return None
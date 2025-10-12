import time
import bpy
import gc
import logging
from add_objects import add_objects_to_scene, add_objects_to_scene_real
from add_objects import empty_scene

logger = logging.getLogger("bpy_execution")


def execute_blender_task_direct(task, real_world=False, gltf_base_dir=None):
    objects_dict, output_path, task_id, color_map, default_scale, default_opacity = task
    
    try:
        
        # Start timing
        start_time = time.time()
        
        # Disable undo for performance
        bpy.context.preferences.edit.use_global_undo = False
        
        # Clear the scene before beginning
        empty_scene()
        
        if real_world:
            result = add_objects_to_scene_real(
                objects_dict=objects_dict,
                output_path=output_path,
                default_scale=default_scale,
                gltf_base_path=gltf_base_dir,
                add_materials=True,
                default_opacity=default_opacity,
                color_map=color_map
            )
        else:
            # Create the model using the add_objects_to_scene function
            result = add_objects_to_scene(
                objects_dict=objects_dict,
                output_path=output_path,
                default_scale=default_scale,
                add_materials=True,
                default_opacity=default_opacity,
                color_map=color_map
            )
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        
        # Clear the scene again to free memory
        empty_scene()
        
        # Force cleanup
        gc.collect()
        
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
            "elapsed_time": elapsed,
            "message": f"Task {task_id} completed in {elapsed:.2f} seconds"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "task_id": task_id,
            "error": str(e),
            "message": f"Error processing {task_id}: {str(e)}"
        }
    

def execute_blender_tasks_direct_sequential(blender_tasks, real_world=False, gltf_base_dir=None):
    if not blender_tasks:
        logger.info("No Blender tasks to execute")
        return {}
    
    logger.info(f"Executing {len(blender_tasks)} Blender tasks sequentially...")
    
    start_time = time.time()
    results = {}
    
    try:
        for i, task in enumerate(blender_tasks, 1):
            task_start_time = time.time()
            
            # Extract task_id for logging (it's the 4th element, index 3)
            task_id = task[2] if len(task) > 3 else f'task_{i}'
            
            logger.info(f"Starting task {i}/{len(blender_tasks)}: {task_id}")
            
            try:
                # Execute the single task
                result = execute_blender_task_direct(task, real_world=real_world, gltf_base_dir=gltf_base_dir)
                results[task_id] = result
                
                task_end_time = time.time()
                task_duration = task_end_time - task_start_time
                
                if result['status'] == 'success':
                    logger.info(f"✓ {result['message']} (completed in {task_duration:.2f}s)")
                else:
                    logger.error(f"✗ {result['message']} (failed after {task_duration:.2f}s)")
                
            except Exception as e:
                task_end_time = time.time()
                task_duration = task_end_time - task_start_time
                
                error_msg = f"Error executing task {task_id}: {str(e)}"
                logger.error(f"✗ {error_msg} (failed after {task_duration:.2f}s)")
                
                results[task_id] = {
                    "status": "error",
                    "task_id": task_id,
                    "error": str(e),
                    "message": error_msg,
                    "execution_time": task_duration
                }
    
    except Exception as e:
        logger.error(f"Critical error in sequential execution: {e}")
        return results
    
    # Summary
    end_time = time.time()
    total_time = end_time - start_time
    
    successes = sum(1 for r in results.values() if r.get('status') == 'success')
    failures = len(results) - successes
    
    logger.info(f"Completed {len(blender_tasks)} Blender tasks sequentially in {total_time:.2f} seconds: "
                f"{successes} successful, {failures} failed")
    logger.info(f"Average time per task: {total_time/len(blender_tasks):.2f} seconds")
    
    return results
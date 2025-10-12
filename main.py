from create_tasks import create_experiment, prepare_experiment
import logging

logging.basicConfig(
    filename='experiment.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


if __name__ == "__main__":
    gltf_base_dir = "your path for 3DComPat++ dataset"

    real_world = True
    dof = 3
    colors = False
    mode = "3D"
    vg_mode = 'circle'  # 3D (sphere or circle), 2D
    # view_kwargs = {
    #     'num_azimuth': 8,
    #     'num_elevation': 4
    # }
    # view_kwargs = {
    #     'azimuths': [45],
    #     'elevations': [70]
    # }
    view_kwargs = {}
    rotation_angle = 0
    multi_agent = False
    show_coords = False
    show_grids = False
    categories = []  # Categories in 3DComPat++
    scale = (0.5, 0.5, 0.5)
    scale = (1.2, 1.2, 1.2)  # Recommend 1.2 for real world object, 0.5 for fundamental primitives

    output_dir = f"./experiments/exp{mode}_{vg_mode}_3_shape"
    image_base_dir = f"./images/exp{mode}_{vg_mode}_3_shape"

    blender_tasks, qa_tuples, csv_path = create_experiment(output_dir=output_dir, num_shapes=2, exp_size=1, dof=dof,
                                                           multi_agent=multi_agent, 
                                                           colors=colors, 
                                                           scale=scale,
                                                           real_world=real_world, categories=categories,
                                                           gltf_base_dir=gltf_base_dir)
    results = prepare_experiment(blender_tasks=blender_tasks, image_base_dir=image_base_dir, 
                                 show_coords=show_coords, show_grid=show_grids, mode=mode, real_world=real_world,
                                 rotation_angle=rotation_angle,
                                 gltf_base_dir=gltf_base_dir,
                                 vg_mode=vg_mode, **view_kwargs)
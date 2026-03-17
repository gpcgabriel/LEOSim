from leosim import *
import dataset as ds
import os
import random
import shutil
import argparse
from plot import (
    compare_algorithms_averaged,
    plot_migrations,
    plot_avg_topology,
    plot_provisioned_in_topology,
    plot_groundstation_links_by_id,
    plot_delay_by_groundstation,
    plot_avg_resource_consumption
)

DATASETS_DIR = "datasets"

ALGORITHMS = {
    "random_allocation": random_allocation,
    "simple_allocation": simple_allocation,
    "best_fit_allocation": best_fit_allocation,
    "longest_duration_allocation": longest_duration_allocation
}

def clear_all_components():
    for cls in ComponentManager.__subclasses__():
        if cls.__name__ != "Simulator":
            cls.clear()

def stopping_criterion(model):
    return model.scheduler.steps == args.num_steps

def main(args):
    os.makedirs(DATASETS_DIR, exist_ok=True)

    algorithm = ALGORITHMS[args.algorithm]

    for rep in range(1, args.repetitions + 1):

        print(f"\n--- Repetition {rep}/{args.repetitions} ---")

        current_seed = rep
        total_resources = 0
        scenario = args.scenario

        # ======================
        # Generate dataset
        # ======================

        clear_all_components()
        random.seed(current_seed)

        print(f"  Generating Dataset: {scenario}")

        t = ds.load_topology(
            args.dataset,
            args.satellites,
            args.num_satellites
        )

        ds.create_users(args.num_users)

        if total_resources == 0:
            total_resources = Satellite.count()

        if scenario == "terrestrial":
            ds.add_process_unit_to_ground_stations(
                t,
                num_process_units=total_resources
            )

        elif scenario == "leo":
            ds.add_process_unit_to_satellites(
                t,
                num_process_units=total_resources
            )

        elif scenario == "hybrid":
            ds.add_process_unit_to_ground_stations(
                t,
                num_process_units=total_resources
            )
            ds.add_process_unit_to_satellites(
                t,
                num_process_units=total_resources
            )

        ds.configure_mobility_models()

        dataset_file = os.path.join(
            DATASETS_DIR,
            f"dataset_rep{rep}_{scenario}.json"
        )

        ComponentManager.save_scenary(filename=dataset_file)

        # ======================
        # Execute simulation
        # ======================
        print(f"  Executing Algorithm: {args.algorithm}")

        log_dir = os.path.join(
            args.logs_dir,
            args.algorithm,
            scenario,
            f"rep{rep}"
        )

        if os.path.exists(log_dir):
            shutil.rmtree(log_dir)

        os.makedirs(log_dir, exist_ok=True)

        sim = Simulator(
            stopping_criterion=stopping_criterion,
            resource_management_algorithm=algorithm,
            topology_management_algorithm=default_topology_management,
            ignore_list=[
                # NetworkFlow,
                # DynamicDurationAccessModel,
                # FixedDurationAccessModel,
                # NetworkLink,
                # Application,
                # ProcessUnit,
                # Satellite,
                # User,
                # GroundStation,
                # Topology
            ],
            clean_data_in_memory=True,
            logs_directory=log_dir
        )

        sim.initialize(dataset_file)
        sim.run()

    # =============
    # Plot results
    # =============
    compare_algorithms_averaged([args.algorithm], [str(args.scenario)], args.repetitions, args.logs_dir)
    plot_migrations([args.algorithm], [str(args.scenario)], args.repetitions, args.logs_dir)
    plot_avg_topology([args.algorithm], [str(args.scenario)], args.repetitions, args.logs_dir)
    plot_provisioned_in_topology([args.algorithm], [str(args.scenario)], args.repetitions, args.logs_dir)
    plot_delay_by_groundstation([args.algorithm], [str(args.scenario)], args.repetitions, args.logs_dir, ground_station_id=1)
    plot_avg_resource_consumption([args.algorithm], [str(args.scenario)], args.repetitions, args.logs_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LEO Simulation Runner")

    parser.add_argument("--dataset", required=True)
    parser.add_argument("--satellites", required=True)
    parser.add_argument("--algorithm", required=True, choices=ALGORITHMS.keys())
    parser.add_argument("--scenario", required=True, choices=["terrestrial", "leo", "hybrid"])
    parser.add_argument("--num_users", type=int, default=100)
    parser.add_argument("--num_satellites", type=int, default=25)
    parser.add_argument("--num_steps", type=int, default=15)
    parser.add_argument("--logs_dir", default="logs")
    parser.add_argument("--repetitions", type=int, default=1)

    args = parser.parse_args()

    main(args)
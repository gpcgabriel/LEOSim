import json
import os
import tempfile
import matplotlib.pyplot as plt
from pathlib import Path

markers = ['o', 'x', 's', '^', 'D', '*', 'v', '+']

def compare_algorithms_averaged(algorithm_names, scenarios, num_repetitions, current_path):
    # Generate a set of graphs for each scenario
    for scenario in scenarios:
        print(f"Processando gráficos para o cenário: {scenario}")
        
        # Dictionaries to store the average data for each algorithm
        # Format: alg_name -> [value_step_0, value_step_1, ...]
        avg_steps = {} 
        avg_provisioned = {}
        avg_delay = {}
        avg_not_provisioned = {}
        
        for algo in algorithm_names:
            # Temporary lists to accumulate data from all repetitions
            # Format: reps_provisioned = [ [prov_rep1_step0, ...], [prov_rep2_step0, ...] ]
            reps_provisioned = []
            reps_delay = []
            reps_not_provisioned = []
            
            captured_steps = [] # Store the X-axis
            
            for rep in range(1, num_repetitions + 1):
                # Path: Algo / Scenario / repX / User.jsonl
                file_path = os.path.join(current_path, algo, scenario, f"rep{rep}", 'User.jsonl')
                
                if not os.path.isfile(file_path):
                    print(f"  WARNING: File not found: {file_path}")
                    continue
                
                curr_steps = []
                curr_prov = []
                curr_delay = []
                curr_not_prov = []
                
                with open(file_path, 'r') as file:
                    last_accesses = {}
                    for line in file:
                        data = json.loads(line)
                        step = data['Step']
                        
                        step_provisioned = 0
                        delay_prov = 0
                        not_provisioned = 0
                        
                        for metric in data['metrics']:
                            current_access = metric['Access to Applications'][0]

                            if last_accesses.get(metric['ID']) is None:
                                last_accesses[metric['ID']] = current_access
                                continue
                            
                            last_access = last_accesses[metric['ID']]
                            
                            if last_access['Request Provisioning'] and (not current_access['Is Provisioned']):
                                not_provisioned += 1
                                
                            elif current_access['Is Provisioned'] or current_access['Provisioning'] == True:
                                step_provisioned += 1
                                delay_prov += current_access['Delay'] if current_access['Delay'] != float('inf') else 0
                            
                            last_accesses[metric['ID']] = current_access
                        
                        curr_steps.append(step)
                        curr_prov.append(step_provisioned)
                        curr_delay.append(delay_prov)
                        curr_not_prov.append(not_provisioned)

                reps_provisioned.append(curr_prov)
                reps_delay.append(curr_delay)
                reps_not_provisioned.append(curr_not_prov)
                
                if not captured_steps:
                    captured_steps = curr_steps
            
            # Calculate Averages (if there is data)
            if reps_provisioned:
                # Determine the minimum length (in case some simulation stopped early)
                min_len = min(len(r) for r in reps_provisioned)
                
                # Helper function for calculating average of a list of lists
                def calc_avg(list_of_lists, length):
                    result = []
                    for i in range(length):
                        soma = sum(l[i] for l in list_of_lists)
                        result.append(soma / len(list_of_lists))
                    return result
                
                avg_steps[algo] = captured_steps[:min_len]
                avg_provisioned[algo] = calc_avg(reps_provisioned, min_len)
                avg_delay[algo] = calc_avg(reps_delay, min_len)
                avg_not_provisioned[algo] = calc_avg(reps_not_provisioned, min_len)
        
        # 1. Provisioned Applications
        plt.figure(figsize=(12, 7))
        for i, algo in enumerate(algorithm_names):
            if algo in avg_provisioned:
                plt.plot(avg_steps[algo], avg_provisioned[algo], label=algo, marker=markers[i % len(markers)])
        plt.xlabel('Step', fontsize=15)
        plt.ylabel('Avg Number of Provisioned Applications', fontsize=15)
        plt.grid(True)
        plt.legend(fontsize=15)
        plt.savefig(os.path.join(current_path, f"provisioned_{scenario}.png"))
        plt.close()

        # 2. Delay
        plt.figure(figsize=(12, 7))
        for i, algo in enumerate(algorithm_names):
            if algo in avg_delay:
                plt.plot(avg_steps[algo], avg_delay[algo], label=algo, marker=markers[i % len(markers)])
        plt.xlabel('Step', fontsize=15)
        plt.ylabel('Delay', fontsize=15)
        plt.grid(True)
        plt.legend(fontsize=15)
        plt.savefig(os.path.join(current_path, f"delay_{scenario}.png"))
        plt.close()

        # 3. Not Provisioned
        plt.figure(figsize=(12, 7))
        for i, algo in enumerate(algorithm_names):
            if algo in avg_not_provisioned:
                plt.plot(avg_steps[algo], avg_not_provisioned[algo], label=algo, marker=markers[i % len(markers)])
        plt.xlabel('Step', fontsize=15)
        plt.ylabel('Avg Applications Not Provisioned', fontsize=15)
        plt.grid(True)
        plt.legend(fontsize=15)
        plt.savefig(os.path.join(current_path, f"not_provisioned_{scenario}.png"))
        plt.close()

def plot_migrations(algorithm_names, scenarios, num_repetitions, current_path):
    # Generate a set of graphs for each scenario
    for scenario in scenarios:
        print(f"Processando gráficos para o cenário: {scenario}")

        avg_migrations = {}
        avg_steps = {}
        
        for alg in algorithm_names:      
            total_migration = []
            captured_steps = [] # To store the X-axis

            for rep in range(1, num_repetitions + 1):
                # Path: Alg / Scenario / repX / Application.jsonl
                if os.path.isfile(os.path.join(current_path, alg, scenario, f"rep{rep}", 'Application.jsonl')):
                    file_path = os.path.join(current_path, alg, scenario, f"rep{rep}", 'Application.jsonl')
                
                if os.path.isfile(os.path.join(current_path, alg, scenario, 'Application.jsonl')):
                    file_path = os.path.join(current_path, alg, scenario, 'Application.jsonl')
                
                if not os.path.isfile(file_path):
                    print(f"  WARNING: File not found: {file_path}")
                    continue
                
                curr_steps = []
                curr_migrations = []
                
                with open(file_path, 'r') as file:
                    for line in file:
                        data = json.loads(line)
                        step = data['Step']
                        
                        step_migrations = 0
                        
                        for metric in data['metrics']:
                            current_access = metric['Last Migration']
                            if current_access is not None and current_access['origin'] is not None and current_access['target'] is not None:
                                step_migrations += 1
                        
                        curr_steps.append(step)
                        curr_migrations.append(step_migrations)

                total_migration.append(curr_migrations)              

                if not captured_steps:
                    captured_steps = curr_steps

            # Calculate averages (if there are repetitions)
            if num_repetitions > 1:
                min_len = min(len(r) for r in total_migration)
                
                def calc_avg(list_of_lists, length):
                    result = []
                    for i in range(length):
                        soma = sum(l[i] for l in list_of_lists)
                        result.append(soma / len(list_of_lists))
                    return result
                
                avg_migrations[alg] = calc_avg(total_migration, min_len)
                avg_steps[alg] = captured_steps[:min_len]
            
            else:
                avg_migrations[alg] = total_migration[0]
                avg_steps[alg] = captured_steps
                
        plt.figure(figsize=(12, 7))
        for i, alg in enumerate(algorithm_names):
            if alg in avg_migrations:
                plt.plot(avg_steps[alg], avg_migrations[alg], label=alg, marker=markers[i % len(markers)])
        plt.xlabel('Step', fontsize=15)
        plt.ylabel('Avg Number of Migrations', fontsize=15)
        plt.grid(True)
        plt.legend(fontsize=15)
        plt.savefig(os.path.join(current_path, f"migrations_{scenario}.png"))
        plt.close()

def plot_avg_topology(algorithm_names, scenarios, num_repetitions, current_path):
    plot_provisioned_in_topology(algorithm_names, scenarios, num_repetitions, current_path)
    
    # Search topologies
    topologies = [
        p.name for p in Path(current_path).iterdir()
        if p.is_dir() and not p.name.startswith('.') and p.name != '__pycache__'
    ]

    final_data = {}

    # Auxiliar structure for graphics:
    # scenario -> topology -> step -> list(migrations)
    scenario_topology_step = {
        scenario: {} for scenario in scenarios
    }

    for topology in topologies:
        final_data[topology] = {}
        topology_path = os.path.join(current_path, topology)

        for alg in algorithm_names:
            final_data[topology][alg] = {}

            for scenario in scenarios:
                total_migration = []
                captured_steps = []

                for rep in range(1, num_repetitions + 1):
                    file_path = os.path.join(
                        topology_path,
                        alg,
                        scenario,
                        f"rep{rep}",
                        "Application.jsonl"
                    )

                    if not os.path.isfile(file_path):
                        print(f"WARNING: File not found: {file_path}")
                        continue

                    curr_steps = []
                    curr_migrations = []

                    with open(file_path, "r") as file:
                        for line in file:
                            data = json.loads(line)
                            step = data["Step"]

                            step_migrations = 0
                            for metric in data["metrics"]:
                                last_migration = metric.get("Last Migration")
                                if (
                                    last_migration
                                    and last_migration.get("origin") is not None
                                    and last_migration.get("target") is not None
                                ):
                                    step_migrations += 1

                            curr_steps.append(step)
                            curr_migrations.append(step_migrations)

                    total_migration.append(curr_migrations)

                    if not captured_steps:
                        captured_steps = curr_steps

                if not total_migration:
                    continue

                # Avg by step (algorithm + repetitions)
                if num_repetitions > 1:
                    min_len = min(len(r) for r in total_migration)
                    avg_migrations = [
                        sum(r[i] for r in total_migration) / len(total_migration)
                        for i in range(min_len)
                    ]
                    steps = captured_steps[:min_len]
                else:
                    avg_migrations = total_migration[0]
                    steps = captured_steps

                # Save JSON
                final_data[topology][alg][scenario] = {}
                for step, avg in zip(steps, avg_migrations):
                    final_data[topology][alg][scenario][str(step)] = {
                        "migrations": avg
                    }

                    # Acumulate for scenary graphics
                    scenario_topology_step.setdefault(scenario, {})
                    scenario_topology_step[scenario].setdefault(topology, {})
                    scenario_topology_step[scenario][topology].setdefault(step, [])
                    scenario_topology_step[scenario][topology][step].append(avg)

    # =========================
    # Create a temporary JSON
    # =========================
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False
    )

    with temp_file as f:
        json.dump(final_data, f, indent=4)

    plot_paths = {}

    for scenario, topo_data in scenario_topology_step.items():
        plt.figure(figsize=(12, 7))

        for idx, (topology, step_data) in enumerate(topo_data.items()):
            steps = sorted(step_data.keys())
            avg_migrations = [
                sum(step_data[s]) / len(step_data[s]) for s in steps
            ]

            marker = markers[idx % len(markers)]
            plt.plot(
                steps,
                avg_migrations,
                marker=marker,
                label=topology
            )

        plt.xlabel("Step", fontsize=15)
        plt.ylabel("Avg Number of Migrations", fontsize=15)
        plt.grid(True)
        plt.legend(fontsize=15)
        plt.tight_layout()

        plot_path = os.path.join(
            current_path,
            f"avg_migrations_topology_vs_step_{scenario}.png"
        )
        plt.savefig(plot_path)
        plt.close()

        plot_paths[scenario] = plot_path

def plot_provisioned_in_topology(algorithm_names, scenarios, num_repetitions, current_path):
    # Search topologies
    topologies = [
        p.name for p in Path(current_path).iterdir()
        if p.is_dir() and not p.name.startswith('.') and p.name != '__pycache__'
    ]

    # scenario -> topology -> step -> list(provisioned)
    scenario_topology_step = {scenario: {} for scenario in scenarios}

    for topology in topologies:
        topology_path = os.path.join(current_path, topology)

        for alg in algorithm_names:
            for scenario in scenarios:
                for rep in range(1, num_repetitions + 1):
                    file_path = os.path.join(
                        topology_path,
                        alg,
                        scenario,
                        f"rep{rep}",
                        "User.jsonl"
                    )

                    if not os.path.isfile(file_path):
                        print(f"AVISO: Arquivo não encontrado: {file_path}")
                        continue

                    last_accesses = {}
                    curr_steps = []
                    curr_provisioned = []

                    with open(file_path, "r") as file:
                        for line in file:
                            data = json.loads(line)
                            step = data["Step"]

                            step_provisioned = 0

                            for metric in data["metrics"]:
                                current_access = metric["Access to Applications"][0]
                                metric_id = metric["ID"]

                                if metric_id not in last_accesses:
                                    last_accesses[metric_id] = current_access
                                    continue

                                last_access = last_accesses[metric_id]

                                if (
                                    current_access["Is Provisioned"]
                                    or current_access.get("Provisioning") is True
                                ):
                                    step_provisioned += 1

                                last_accesses[metric_id] = current_access

                            curr_steps.append(step)
                            curr_provisioned.append(step_provisioned)

                    # Store by scenario/topology/step
                    for step, prov in zip(curr_steps, curr_provisioned):
                        scenario_topology_step.setdefault(scenario, {})
                        scenario_topology_step[scenario].setdefault(topology, {})
                        scenario_topology_step[scenario][topology].setdefault(step, [])
                        scenario_topology_step[scenario][topology][step].append(prov)

    # ===============================
    # Create graphs for each scenario
    # ===============================
    plot_paths = {}

    for scenario, topo_data in scenario_topology_step.items():
        plt.figure(figsize=(12, 7))

        for idx, (topology, step_data) in enumerate(topo_data.items()):
            steps = sorted(step_data.keys())
            avg_provisioned = [
                sum(step_data[s]) / len(step_data[s]) for s in steps
            ]

            marker = markers[idx % len(markers)]
            plt.plot(
                steps,
                avg_provisioned,
                marker=marker,
                label=topology
            )

        plt.xlabel("Step", fontsize=15)
        plt.ylabel("Avg Number of Provisioned Users", fontsize=15)
        plt.grid(True)
        plt.legend(fontsize=15)
        plt.tight_layout()

        plot_path = os.path.join(
            current_path,
            f"avg_provisioned_topology_vs_step_{scenario}.png"
        )
        plt.savefig(plot_path)
        plt.close()

        plot_paths[scenario] = plot_path

def plot_groundstation_links_by_id(algorithm_names, scenarios, num_repetitions, current_path, ground_station_id):
    """
    Plots the temporal evolution of the number of links for a specific ground station.
    For each scenario, generates a graph comparing the algorithms.
    """
    for scenario in scenarios:
        print(f"Processing links from ground station {ground_station_id} for scenario: {scenario}")
        
        avg_links = {}   # algorithm -> list with avg by step
        avg_steps = {}   # algorithm -> list with corresponding steps
        
        for algo in algorithm_names:
            reps_links = []       # list of lists (one per repetition)
            captured_steps = []   # steps from the first repetition (reference)
            
            for rep in range(1, num_repetitions + 1):
                file_path = os.path.join(current_path, algo, scenario, f"rep{rep}", 'GroundStation.jsonl')
                if not os.path.isfile(file_path):
                    print(f"  WARNING: File not found: {file_path}")
                    continue
                
                curr_steps = []
                curr_links = []
                with open(file_path, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        step = data['Step']
                        # Search a ground station with the desired ID
                        found = False
                        for gs in data['metrics']:
                            if gs['ID'] == ground_station_id:
                                curr_links.append(gs['Count'])
                                curr_steps.append(step)
                                found = True
                                break
                        if not found:
                            # Optional: emit warning if the station is not found in some step
                            print(f"  WARNING: Ground station {ground_station_id} not found in step {step} of file {file_path}")
                
                if curr_links:
                    reps_links.append(curr_links)
                    if not captured_steps:
                        captured_steps = curr_steps
            
            # Calculate averages if there are repetitions
            if reps_links:
                min_len = min(len(r) for r in reps_links)
                avg = [sum(r[i] for r in reps_links) / len(reps_links) for i in range(min_len)]
                avg_links[algo] = avg
                avg_steps[algo] = captured_steps[:min_len]
        
        plt.figure(figsize=(12, 7))
        for i, algo in enumerate(algorithm_names):
            if algo in avg_links:
                plt.plot(avg_steps[algo], avg_links[algo], 
                         label=algo, marker=markers[i % len(markers)])
        plt.xlabel('Step')
        plt.ylabel(f'Number of satellites connected to GroundStation_{ground_station_id}')
        plt.grid(True)
        plt.savefig(os.path.join(current_path, f"gs_{ground_station_id}_links_{scenario}.png"))
        plt.close()
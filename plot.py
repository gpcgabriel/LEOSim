import json
import os
import matplotlib.pyplot as plt
from pathlib import Path

markers = ['o', 'x', 's', '^', 'D', '*', 'v', '+']

# ==========================================================
# UTILITY FUNCTIONS
# ==========================================================
def read_jsonl(file_path):
    with open(file_path) as f:
        for line in f:
            yield json.loads(line)

def calculate_average(list_of_lists):
    if not list_of_lists:
        return []

    min_len = min(len(l) for l in list_of_lists)

    return [
        sum(l[i] for l in list_of_lists) / len(list_of_lists)
        for i in range(min_len)
    ]

def plot(data_dict, steps_dict, xlabel, ylabel, filename, current_path):
    plt.figure(figsize=(12, 7))

    for i, label in enumerate(data_dict):

        plt.plot(
            steps_dict[label],
            data_dict[label],
            label=label,
            marker=markers[i % len(markers)]
        )

    plt.xlabel(xlabel, fontsize=18)
    plt.ylabel(ylabel, fontsize=18)
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)
    plt.grid(True)
    plt.legend(fontsize=15)

    plt.savefig(os.path.join(current_path, filename))
    plt.close()

def get_topologies(current_path):
    return [
        p.name for p in Path(current_path).iterdir()
        if p.is_dir() and not p.name.startswith('.') and p.name != '__pycache__'
    ]

def build_path(current_path, alg, scenario, filename, rep=None):
    """
    Build the correct file path considering if repetitions exist or not.
    """
    if rep is None:
        return os.path.join(
            current_path,
            alg,
            scenario,
            "rep1",
            filename
        )

    return os.path.join(
        current_path,
        alg,
        scenario,
        f"rep{rep}",
        filename
    )

# ==========================================================
# USER METRICS
# ==========================================================
def compare_algorithms_averaged(algorithm_names, scenarios, num_repetitions, current_path):
    for scenario in scenarios:

        print(f"Processing scenario: {scenario}")

        avg_provisioned = {}
        avg_delay = {}
        avg_not_provisioned = {}
        avg_steps = {}

        for alg in algorithm_names:

            reps_prov = []
            reps_delay = []
            reps_not = []
            captured_steps = []

            for rep in range(1, num_repetitions + 1):

                if num_repetitions == 1:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "User.jsonl"
                    )
                else:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "User.jsonl",
                        rep
                    )

                if not os.path.isfile(file_path):
                    print(f"WARNING: {file_path} not found")
                    continue

                curr_steps = []
                curr_prov = []
                curr_delay = []
                curr_not = []

                last_accesses = {}

                for data in read_jsonl(file_path):

                    step = data["Step"]

                    step_prov = 0
                    delay = 0
                    not_prov = 0

                    for metric in data["metrics"]:

                        current = metric["Access to Applications"][0]

                        if metric["ID"] not in last_accesses:
                            last_accesses[metric["ID"]] = current
                            continue

                        last = last_accesses[metric["ID"]]

                        if last["Request Provisioning"] and not current["Is Provisioned"]:
                            not_prov += 1

                        elif current["Is Provisioned"] or current["Provisioning"]:

                            step_prov += 1

                            if current["Delay"] != float("inf"):
                                delay += current["Delay"]

                        last_accesses[metric["ID"]] = current

                    curr_steps.append(step)
                    curr_prov.append(step_prov)
                    curr_delay.append(delay)
                    curr_not.append(not_prov)

                reps_prov.append(curr_prov)
                reps_delay.append(curr_delay)
                reps_not.append(curr_not)

                if not captured_steps:
                    captured_steps = curr_steps

            if reps_prov:

                avg_provisioned[alg] = calculate_average(reps_prov)
                avg_delay[alg] = calculate_average(reps_delay)
                avg_not_provisioned[alg] = calculate_average(reps_not)

                min_len = len(avg_provisioned[alg])
                avg_steps[alg] = captured_steps[:min_len]

        plot(
            avg_provisioned,
            avg_steps,
            "Step",
            "Avg Number of Provisioned Applications",
            f"provisioned_{scenario}.png",
            current_path
        )

        plot(
            avg_delay,
            avg_steps,
            "Step",
            "Delay",
            f"delay_{scenario}.png",
            current_path
        )

        plot(
            avg_not_provisioned,
            avg_steps,
            "Step",
            "Avg Applications Not Provisioned",
            f"not_provisioned_{scenario}.png",
            current_path
        )

# ==========================================================
# MIGRATIONS
# ==========================================================
def plot_migrations(algorithm_names, scenarios, num_repetitions, current_path):

    for scenario in scenarios:

        print(f"Processing migrations for scenario: {scenario}")

        avg_migrations = {}
        avg_steps = {}

        for alg in algorithm_names:

            total_migrations = []
            captured_steps = []

            for rep in range(1, num_repetitions + 1):

                if num_repetitions == 1:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "Application.jsonl"
                    )
                else:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "Application.jsonl",
                        rep
                    )

                if not os.path.isfile(file_path):
                    continue

                curr_steps = []
                curr_migrations = []

                for data in read_jsonl(file_path):

                    step = data["Step"]

                    migrations = sum(
                        1 for metric in data["metrics"]
                        if metric.get("Last Migration")
                        and metric["Last Migration"].get("origin") is not None
                        and metric["Last Migration"].get("target") is not None
                    )

                    curr_steps.append(step)
                    curr_migrations.append(migrations)

                total_migrations.append(curr_migrations)

                if not captured_steps:
                    captured_steps = curr_steps

            if total_migrations:

                avg_migrations[alg] = calculate_average(total_migrations)

                min_len = len(avg_migrations[alg])
                avg_steps[alg] = captured_steps[:min_len]

        plot(
            avg_migrations,
            avg_steps,
            "Step",
            "Avg Number of Migrations",
            f"migrations_{scenario}.png",
            current_path
        )

# ==========================================================
# TOPOLOGY ANALYSIS
# ==========================================================
def plot_avg_topology(algorithm_names, scenarios, num_repetitions, current_path):

    plot_provisioned_in_topology(
        algorithm_names,
        scenarios,
        num_repetitions,
        current_path
    )

    topologies = get_topologies(current_path)

    scenario_topology_step = {scenario: {} for scenario in scenarios}

    for topology in topologies:

        topology_path = os.path.join(current_path, topology)

        for alg in algorithm_names:

            for scenario in scenarios:

                for rep in range(1, num_repetitions + 1):

                    if num_repetitions == 1:
                        file_path = build_path(
                            current_path,
                            alg,
                            scenario,
                            "Application.jsonl"
                        )
                    else:
                        file_path = build_path(
                            current_path,
                            alg,
                            scenario,
                            "Application.jsonl",
                            rep
                        )

                    if not os.path.isfile(file_path):
                        continue

                    for data in read_jsonl(file_path):

                        step = data["Step"]

                        migrations = sum(
                            1 for metric in data["metrics"]
                            if metric.get("Last Migration")
                            and metric["Last Migration"].get("origin") is not None
                            and metric["Last Migration"].get("target") is not None
                        )

                        scenario_topology_step \
                            .setdefault(scenario, {}) \
                            .setdefault(topology, {}) \
                            .setdefault(step, []) \
                            .append(migrations)

    for scenario, topo_data in scenario_topology_step.items():

        data = {}
        steps = {}

        for topology, step_data in topo_data.items():

            sorted_steps = sorted(step_data.keys())

            data[topology] = [
                sum(step_data[s]) / len(step_data[s])
                for s in sorted_steps
            ]

            steps[topology] = sorted_steps

        plot(
            data,
            steps,
            "Step",
            "Avg Number of Migrations",
            f"avg_migrations_topology_vs_step_{scenario}.png",
            current_path
        )

# ==========================================================
# PROVISIONED USERS BY TOPOLOGY
# ==========================================================
def plot_provisioned_in_topology(algorithm_names, scenarios, num_repetitions, current_path):

    topologies = get_topologies(current_path)

    scenario_topology_step = {scenario: {} for scenario in scenarios}

    for topology in topologies:

        topology_path = os.path.join(current_path, topology)

        for alg in algorithm_names:

            for scenario in scenarios:

                for rep in range(1, num_repetitions + 1):

                    if num_repetitions == 1:
                        file_path = build_path(
                            current_path,
                            alg,
                            scenario,
                            "User.jsonl"
                        )
                    else:
                        file_path = build_path(
                            current_path,
                            alg,
                            scenario,
                            "User.jsonl",
                            rep
                        )

                    if not os.path.isfile(file_path):
                        continue

                    last_accesses = {}

                    for data in read_jsonl(file_path):

                        step = data["Step"]

                        prov = 0

                        for metric in data["metrics"]:

                            current = metric["Access to Applications"][0]
                            metric_id = metric["ID"]

                            if metric_id not in last_accesses:
                                last_accesses[metric_id] = current
                                continue

                            if current["Is Provisioned"] or current.get("Provisioning"):
                                prov += 1

                            last_accesses[metric_id] = current

                        scenario_topology_step \
                            .setdefault(scenario, {}) \
                            .setdefault(topology, {}) \
                            .setdefault(step, []) \
                            .append(prov)

    for scenario, topo_data in scenario_topology_step.items():

        data = {}
        steps = {}

        for topology, step_data in topo_data.items():

            sorted_steps = sorted(step_data.keys())

            data[topology] = [
                sum(step_data[s]) / len(step_data[s])
                for s in sorted_steps
            ]

            steps[topology] = sorted_steps

        plot(
            data,
            steps,
            "Step",
            "Avg Number of Provisioned Users",
            f"avg_provisioned_topology_vs_step_{scenario}.png",
            current_path
        )

# ==========================================================
# GROUND STATION LINKS
# ==========================================================
def plot_groundstation_links_by_id(
        algorithm_names,
        scenarios,
        num_repetitions,
        current_path,
        ground_station_id
):

    for scenario in scenarios:

        print(f"Processing GroundStation {ground_station_id} scenario: {scenario}")

        avg_links = {}
        avg_steps = {}

        for alg in algorithm_names:

            reps_links = []
            captured_steps = []

            for rep in range(1, num_repetitions + 1):

                if num_repetitions == 1:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "GroundStation.jsonl"
                    )
                else:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "GroundStation.jsonl",
                        rep
                    )

                if not os.path.isfile(file_path):
                    continue

                curr_steps = []
                curr_links = []

                for data in read_jsonl(file_path):

                    step = data["Step"]

                    for gs in data["metrics"]:
                        if gs["ID"] == ground_station_id:
                            curr_steps.append(step)
                            curr_links.append(gs["Count"])
                            break

                if curr_links:
                    reps_links.append(curr_links)

                    if not captured_steps:
                        captured_steps = curr_steps

            if reps_links:

                avg_links[alg] = calculate_average(reps_links)

                min_len = len(avg_links[alg])
                avg_steps[alg] = captured_steps[:min_len]

        plot(
            avg_links,
            avg_steps,
            "Step",
            f"Number of satellites connected to GroundStation_{ground_station_id}",
            f"gs_{ground_station_id}_links_{scenario}.png",
            current_path
        )

# ==========================================================
# GROUND STATION DELAY
# ==========================================================
def plot_delay_by_groundstation(algorithm_names, scenarios, num_repetitions, current_path, ground_station_id):
    for scenario in scenarios:
        print(f"Processing delay for GS {ground_station_id} - scenario: {scenario}")

        avg_delay = {}
        avg_steps = {}

        for alg in algorithm_names:

            reps_delay = []
            captured_steps = []

            for rep in range(1, num_repetitions + 1):

                if num_repetitions == 1:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "User.jsonl"
                    )
                else:
                    file_path = build_path(
                        current_path,
                        alg,
                        scenario,
                        "User.jsonl",
                        rep
                    )

                if not os.path.isfile(file_path):
                    continue

                curr_steps = []
                curr_delay = []

                for data in read_jsonl(file_path):

                    step = data["Step"]
                    step_delay = 0

                    for metric in data["metrics"]:

                        # Filtra apenas usuários conectados à GS desejada
                        if f"GroundStation_{ground_station_id}" not in metric.get("Network Access Points", []):
                            continue

                        current = metric["Access to Applications"][0]

                        if current["Is Provisioned"] or current.get("Provisioning"):

                            d = current.get("Delay", 0)

                            if d != float("inf") and d is not None:
                                step_delay += d

                    curr_steps.append(step)
                    curr_delay.append(step_delay)

                if curr_delay:
                    reps_delay.append(curr_delay)

                    if not captured_steps:
                        captured_steps = curr_steps

            if reps_delay:

                avg_delay[alg] = calculate_average(reps_delay)

                min_len = len(avg_delay[alg])
                avg_steps[alg] = captured_steps[:min_len]

        plot(avg_delay, avg_steps, "Step", f"Delay (GS {ground_station_id})", f"delay_gs_{ground_station_id}_{scenario}.png", current_path)
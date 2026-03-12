# LEOSim
LEOSim is a Python-based simulation framework designed to model and evaluate resource management in integrated terrestrial-satellite networks. The simulator allows for the analysis of different resource allocation algorithms across terrestrial, satellite (LEO), and hybrid scenarios.

## 🚀 Getting Started
### Prerequisites
Ensure you have Python 3.8 or higher installed on your machine.

## 📦 Installation

#### 1. Clone the repository:

```bash
git clone https://github.com/gpcgabriel/LEOSim.git
cd LEOSim
```
#### 2. Install the required dependences:
```bash
pip install -r requirements.txt
```
*Key dependencies include networkx for topology management and matplotlib for visualization.*
    
## 🛠️ Configuring Your Simulation
The simulator is centered around the `Simulator` object, which coordinates components, topology, and event scheduling.

#### Basic Usage Example
You can create a simple script to run a simulation:
```python3
from galeos import *

# 1. Define the stopping criterion (e.g., 50 steps)
def stopping_criterion(model):
    return model.scheduler.steps == 50

# 2. Configure the simulator
sim = Simulator(
    stopping_criterion=stopping_criterion,
    resource_management_algorithm=simple_allocation, # Allocation algorithm
    logs_directory="my_logs",
    clean_data_in_memory=True
)

# 3. Initialize with a scenario (JSON file)
sim.initialize("datasets/example.json")

# 4. Run
sim.run()
```

## ▶️ Running Tests
If you want to use the script we created, run:

```bash
python main.py \
--dataset datasets/rnp.gml \
--satellites datasets/satellites_brazil.json \
--algorithm longest_duration_allocation \
--scenario hybrid \
--num_users 10 \
--num_satellites 2 \
--num_steps 5 \
--logs_dir logs
```

## 🏗️ Project Structure
- `galeos/`: Core of the simulator, containing the simulation engine (simulator.py) and the scheduler (scheduler.py).

- `galeos/components/`: Definitions of system agents such as Satellite, User, GroundStation, and ProcessUnit.

- `galeos/components/allocation_algorithms/`: Implementations of allocation strategies (e.g., Best Fit, Random, Simple).

- `datasets/`: Topology files (GML) and pre-configured scenarios.

- `main.py`: Main script for running large-scale experiments with multiple repetitions and scenarios`.

## 📊 Data Collection and Results
#### GALEOS automatically generates log files in `.jsonl` format within the specified directory.

- Each component class (e.g., `Satellite`, `User`) generates its own metrics file.

- The simulator performs periodic data dumps to `revent excessive memory consumption.

- Use the `plot` module to generate comparative charts after execution.
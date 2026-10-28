# Adaptive 5G Resource Allocation and QoS Optimization

This project studies resource allocation for three 5G network slices:

- **eMBB**: high-throughput traffic
- **URLLC**: low-latency, reliable traffic
- **mMTC**: many low-rate IoT devices

The project contains the original ns-3 static-allocation experiment and a
native Python DQN controller connected to ns-3 through the `ns3-ai` Gymnasium
interface.

## Repository contents

```text
code/
  slicing-sim.cc              ns-3 simulation and slice environment
  native_dqn.py               PyTorch DQN client for native ns-3 control
  adaptive_slicing.py         fast Python policy prototype
  run_adaptive_experiments.py static/random/adaptive prototype comparison
  plot_results.py             static-result plot generation
  draw_diagrams.py            architecture diagram generation
  streamlit_app.py            results dashboard

paper/
  main.tex                    LaTeX report

deck/
  build_deck.js               presentation source

results/
  run*_timeseries.csv         static ns-3 results
  figs_light/, figs_dark/     generated figures
  adaptive/                   Python prototype results
  native_*.csv                native ns-3 adaptive results
  native_dqn.pt               saved DQN model
```

## Requirements

### Python

Use Python 3.12. Python 3.15 is not supported by the native PyTorch workflow.

### Native tools

- macOS 15 or newer, or a Linux system
- C/C++ compiler
- CMake and Ninja
- Git
- Boost
- Protocol Buffers
- pybind11
- ns-3.45
- ns3-ai

The commands below are for Apple Silicon macOS with Homebrew. Adjust paths
for Linux or Intel macOS.

## 1. Clone the project

```bash
git clone <YOUR_REPOSITORY_URL>
cd slicing_midsem_source
```

## 2. Install system dependencies

```bash
brew update
brew install python@3.12 cmake ninja pkg-config git boost protobuf pybind11
xcode-select --install
```

If Command Line Tools are already installed, macOS will report that no action
is needed.

## 3. Create the Python environment

```bash
/opt/homebrew/bin/python3.12 -m venv .venv312
source .venv312/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the Python environment:

```bash
python - <<'PY'
import numpy, pandas, matplotlib, streamlit, gymnasium, torch
print("Python requirements: OK")
print("PyTorch:", torch.__version__)
PY
```

## 4. Install and build ns-3.45

Keep ns-3 outside this repository:

```bash
mkdir -p ~/ns3
cd ~/ns3

git clone --depth 1 --branch ns-3.45 \
  https://gitlab.com/nsnam/ns-3-dev.git ns-3.45

cd ns-3.45
/opt/homebrew/bin/python3.12 ./ns3 configure \
  --enable-examples \
  --enable-tests
/opt/homebrew/bin/python3.12 ./ns3 build
```

## 5. Install and build ns3-ai

Clone the current ns3-ai repository into the ns-3 `contrib` directory:

```bash
cd ~/ns3/ns-3.45

git clone --depth 1 \
  https://github.com/hust-diangroup/ns3-ai.git contrib/ai

source ~/path/to/slicing_midsem_source/.venv312/bin/activate
python -m pip install -e contrib/ai/python_utils
python -m pip install -e contrib/ai/model/gym-interface/py

/opt/homebrew/bin/python3.12 ./ns3 configure \
  --enable-examples \
  --enable-tests \
  -- \
  -DPython_EXECUTABLE="$VIRTUAL_ENV/bin/python" \
  -DPython3_EXECUTABLE="$VIRTUAL_ENV/bin/python"

/opt/homebrew/bin/python3.12 ./ns3 build ai
/opt/homebrew/bin/python3.12 ./ns3 build ns3ai_apb_gym
```

The A+B example is an optional bridge smoke test:

```bash
cd ~/ns3/ns-3.45/contrib/ai/examples/a-plus-b/use-gym
PYTHONPATH=~/ns3/ns-3.45/contrib/ai/model/gym-interface/py \
  python apb.py
```

## 6. Build the project simulator

Copy the simulator into the ns-3 scratch directory:

```bash
PROJECT_ROOT="$HOME/path/to/slicing_midsem_source"

cp "$PROJECT_ROOT/code/slicing-sim.cc" ~/ns3/ns-3.45/scratch/slicing-sim.cc

cd ~/ns3/ns-3.45
/opt/homebrew/bin/python3.12 ./ns3 build slicing-sim
```

The source is kept in this repository; the copy in `scratch/` is the file
compiled by ns-3.

## 7. Run the static ns-3 simulation

```bash
cd ~/ns3/ns-3.45
/opt/homebrew/bin/python3.12 ./ns3 run \
  "slicing-sim --run=1 --out=$PROJECT_ROOT/results/ns3_static_run1"
```

This produces:

```text
results/ns3_static_run1_timeseries.csv
```

The static baseline uses the `50/30/20` allocation by default. You can
override it:

```bash
/opt/homebrew/bin/python3.12 ./ns3 run \
  "slicing-sim --run=2 --alloc=60,25,15 --out=$PROJECT_ROOT/results/custom_run"
```

## 8. Run the fast Python comparison

This does not require ns-3:

```bash
cd "$PROJECT_ROOT"
source .venv312/bin/activate
python code/run_adaptive_experiments.py
```

Outputs are written to:

```text
results/adaptive/
```

## 9. Run the native DQN controller

The native environment uses:

- 10-dimensional observation
- 36 discrete allocation actions
- 1-second control interval
- 64-64 PyTorch DQN
- replay buffer
- target network
- epsilon-greedy exploration

### Train

```bash
cd "$PROJECT_ROOT"
source .venv312/bin/activate

PYTHONPATH="$HOME/ns3/ns-3.45/contrib/ai/model/gym-interface/py" \
python code/native_dqn.py \
  --ns3 "$HOME/ns3/ns-3.45" \
  --train \
  --run 20 \
  --model results/native_dqn.pt \
  --out results/native_train_run20
```

The model is saved to:

```text
results/native_dqn.pt
```

The simulator output is saved as:

```text
results/native_train_run20_timeseries.csv
```

### Evaluate

```bash
PYTHONPATH="$HOME/ns3/ns-3.45/contrib/ai/model/gym-interface/py" \
python code/native_dqn.py \
  --ns3 "$HOME/ns3/ns-3.45" \
  --run 21 \
  --model results/native_dqn.pt \
  --epsilon 0.05 \
  --out results/native_eval_run21
```

## 10. Run the native policy comparison benchmark

This produces a fair native ns-3 comparison for static, random, adaptive, and DQN across multiple seeds:

```bash
cd "$PROJECT_ROOT"
source .venv312/bin/activate
PYTHONPATH="$HOME/ns3/ns-3.45/contrib/ai/model/gym-interface/py" \
python code/native_policy_comparison.py \
  --ns3 "$HOME/ns3/ns-3.45" \
  --runs 3 \
  --policies static,random,adaptive,dqn
```

This writes a combined summary to:

```text
results/native_policy_compare/overall_summary.csv
```

and saves a policy-delay chart to:

```text
results/native_policy_compare/policy_delay_comparison.png
```

## 11. Open the dashboard

```bash
cd "$PROJECT_ROOT"
source .venv312/bin/activate
streamlit run code/streamlit_app.py
```

Open the address printed by Streamlit, normally:

```text
http://localhost:8501
```

Stop the dashboard with `Ctrl+C`.

## 12. Generate static figures

```bash
cd "$PROJECT_ROOT"
source .venv312/bin/activate

python code/plot_results.py \
  --results results \
  --out results/figs_light \
  --theme light

python code/plot_results.py \
  --results results \
  --out results/figs_dark \
  --theme dark

python code/draw_diagrams.py \
  --out results/figs_light \
  --theme light

python code/draw_diagrams.py \
  --out results/figs_dark \
  --theme dark
```

## Troubleshooting

### `torch` cannot be imported

Make sure the Python 3.12 environment is active:

```bash
source .venv312/bin/activate
python --version
python -c "import torch; print(torch.__version__)"
```

### ns-3 launcher fails with Python 3.15

Always invoke ns-3 through Python 3.12:

```bash
/opt/homebrew/bin/python3.12 ./ns3 build
/opt/homebrew/bin/python3.12 ./ns3 run "slicing-sim --run=1"
```

### `messages_pb2` cannot be imported

Set the ns3-ai Gym Python path:

```bash
export PYTHONPATH="$HOME/ns3/ns-3.45/contrib/ai/model/gym-interface/py"
```

### Model or output path cannot be found

Use paths relative to the project root and run the Python command from the
project root. The native client also resolves project-relative paths.

### ns3-ai build cannot find Boost

Install the native dependencies and reconfigure:

```bash
brew install boost protobuf pybind11
cd ~/ns3/ns-3.45
/opt/homebrew/bin/python3.12 ./ns3 configure --enable-examples --enable-tests
/opt/homebrew/bin/python3.12 ./ns3 build ai
```

## Current project status

Implemented and verified:

- ns-3.45 static slicing simulation
- eMBB, URLLC, and mMTC traffic phases
- runtime `ApplyAllocation()` control
- native ns3-ai Gym bridge
- 36-action adaptive allocation environment
- PyTorch DQN training and evaluation
- static/random/adaptive prototype comparison
- Streamlit dashboard
- generated static and native result CSV files

The optional next step is to run many independent training/evaluation seeds
and update the paper and presentation with averaged native-DQN results and
confidence intervals.

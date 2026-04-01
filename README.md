# Unrealized Expectations: Comparing AI Methods vs Classical Algorithms for Maximum Independent Set

This repository contains the code and notes used for the paper *Unrealized Expectations: Comparing AI Methods vs Classical Algorithms for Maximum Independent Set*.

At a high level, the repository is organized around three pieces of the study:

- `data/`: random graph generation utilities used to build MIS datasets.
- `ltft/`: evaluation code and notes for the LTFT / GFlowNet-based experiments, with a focus on degree-based action analysis.
- `serialization/`: analysis code for the serialization-style degree-greedy comparison described in the paper.

This is a lightweight research-code repository rather than a fully packaged software project. Some scripts are self-contained, while others are designed to be used inside larger upstream codebases.

## Repository Structure

```text
MIS-UnExp/
├── README.md
├── data/
│   ├── random_graph.py
│   └── random_graph.md
├── ltft/
│   ├── evaluate.py
│   └── evaluate.md
└── serialization/
    ├── compare_greedy.py
    ├── compare_greedy_segment.py
    ├── compare_greedy_folders.py
    └── compare_greedy.md
```

## Folder Guide

### `data/`

This folder contains code for random graph generation. It extends the MIS benchmark framework with additional graph samplers so experiments can be run on a broader set of controlled synthetic graph families.

Main files:

- `data/random_graph.py`: implements graph samplers and dataset generation logic.
- `data/random_graph.md`: documents the sampler classes, generator behavior, and related dependencies.

What the script is for:

- generating random MIS benchmark instances;
- supporting both variable-size and fixed-size graph families;
- optionally attaching node weights and MIS labels when used with the upstream benchmark framework.

Graph families covered in the code/docs include:

- Erdős-Rényi and `G(n, m)` random graphs;
- Barabási-Albert and Holme-Kim graphs;
- Watts-Strogatz graphs;
- hyperbolic random graphs;
- additional fixed-size variants such as `GND`, `Regular`, `BA_n_m`, `HK_n_m_p`, and `WS_n_k_p`.

Important note:

`data/` is meant to be used inside the upstream [MIS benchmark framework](https://github.com/MaxiBoether/mis-benchmark-framework). In particular, `random_graph.py` expects components such as `DataGenerator` and helper utilities from that codebase, and the hyperbolic generator also relies on the external `girgs` project.

### `ltft/`

This folder contains the evaluation script and documentation for the LTFT-related experiments, specifically the degree-based analysis used with the GFlowNet MIS setup.

Main files:

- `ltft/evaluate.py`: runs evaluation of a trained policy on MIS test graphs and writes output files.
- `ltft/evaluate.md`: explains how the evaluation works and how the degree-based ranking statistics should be interpreted.

What the script is for:

- loading a trained LTFT / GFlowNet policy;
- running repeated stochastic rollouts on test graphs;
- saving the best independent set found for each graph as a `.result` file;
- recording how often the model's actions align with low-degree choices during rollout.

Outputs described in the code/docs:

- `.result` files: one binary vector per graph, indicating the selected independent set;
- `rankings.out`: raw per-step degree-ranking information;
- `stats.out`: aggregate percentages for rank-1, top-5%, and top-10% degree alignment.

Important note:

`ltft/` is intended for use with the upstream [GFlowNet-CombOpt](https://github.com/zdhNarsil/GFlowNet-CombOpt) repository. `evaluate.py` depends on that larger training/evaluation codebase, including modules such as `data`, `util`, `algorithm`, Hydra configs, PyTorch, and DGL, so it should be understood as the evaluation entry point used in the paper rather than a standalone script that can be run in isolation from this repository alone.

### `serialization/`

This folder contains the code for the serialization analysis described in the paper.

Main files:

- `serialization/compare_greedy.py`: analyzes one graph and one result file.
- `serialization/compare_greedy_segment.py`: analyzes a directory of graph/result pairs and reports per-graph and aggregate statistics.
- `serialization/compare_greedy_folders.py`: compares multiple result directories against the same graph set and writes an aggregated summary.
- `serialization/compare_greedy.md`: documents the shared analysis logic, assumptions, and command-line usage.

What the scripts are for:

- validating that a predicted solution is an independent set;
- repeatedly simulating a randomized degree-based greedy removal process;
- measuring how often the chosen MIS nodes match the current lowest-degree nodes;
- summarizing agreement using `rank == 1`, top-5%, and top-10% statistics;
- comparing one solver, one experiment folder, or many experiment folders side by side.

For the full motivation and methodological details of the serialization analysis, please refer to the paper.

## Shared Data Format

Several scripts in this repository assume the following file formats:

- graph instances are stored as NetworkX `.gpickle` files;
- solver outputs are stored as text files with one `0` or `1` per line;
- each `1` indicates that the corresponding node is included in the independent set.

For the analysis to be valid, the ordering of entries in the solution vector must match the node ordering used when the graph was serialized.

## Required Packages

The exact environment depends on which part of the repository you want to use.

### Common packages

- `python`
- `networkx`
- `numpy`

### For `serialization/`

These scripts are the most lightweight part of the repository and mainly require:

- `networkx`
- `numpy`

### For `data/`

To use `data/random_graph.py` inside the MIS benchmark framework, the relevant environment should include:

- `networkx`
- `tqdm`
- `logzero`

In addition, this code depends on the surrounding [MIS benchmark framework](https://github.com/MaxiBoether/mis-benchmark-framework), which provides classes such as `DataGenerator`, helper utilities, and the broader experiment environment. If you generate labels, the benchmark framework's solver dependencies are also required.

### For `ltft/`

To use `ltft/evaluate.py` inside the GFlowNet codebase, the relevant environment should include:

- `tqdm`
- `hydra-core`
- `omegaconf`
- `torch`
- `dgl`
- `einops`
- `numpy`

This code is intended to run inside [GFlowNet-CombOpt](https://github.com/zdhNarsil/GFlowNet-CombOpt), so its local modules and configuration files are also required.

## How the Pieces Fit Together

The repository reflects the workflow used in the paper:

1. Generate or prepare random graph instances in `data/` inside the MIS benchmark framework.
2. Evaluate LTFT / GFlowNet models in `ltft/` inside the GFlowNet-CombOpt codebase and save `.result` outputs.
3. Run the serialization-style degree-greedy analysis in `serialization/` to compare learned behavior and classical greedy structure.

In that sense:

- `data/` supports dataset creation within the MIS benchmark framework;
- `ltft/` supports model evaluation and degree-based behavioral logging within GFlowNet-CombOpt;
- `serialization/` supports the paper's comparison analysis used to interpret solutions.

## Practical Notes

- There is no packaged installation setup in this repository.
- `data/` should be used with the MIS benchmark framework.
- `ltft/` should be used with GFlowNet-CombOpt.
- `serialization/` is documented here, but the paper should be treated as the primary reference for the detailed method.
- The markdown files in each folder are the best place to start if you want the exact assumptions, CLI arguments, and interpretation details for a given script.

## Recommended Starting Points

- Read `data/random_graph.md` for graph generation details.
- Read `ltft/evaluate.md` for LTFT evaluation outputs and the degree-ranking metric.
- Read `serialization/compare_greedy.md` for the serialization analysis logic and when to use each analysis script.
# MIS-UnExp

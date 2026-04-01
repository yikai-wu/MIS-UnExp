# Degree-based greedy (Deg-greedy) and Random greedy (Ran-greedy) 

This note documents two greedy baselines that generate `.result` files for graphs stored as `.gpickle` files:

- `deg_greedy_result.py`
- `random_greedy_result.py`

Both scripts are intended to produce solution files in the same format used elsewhere in the repository. For each graph, they construct one heuristic independent set, write that set as a binary `.result` file, and also record the size of the generated solution.

---

## Shared workflow

The two scripts follow the same outer pipeline.

1. Read each graph from a `.gpickle` file.
2. Construct one heuristic independent set.
3. Save the independent set as a `.result` file with one `0` or `1` per line.
4. Record the size of the independent set.
5. Process all graph files in the input folder in parallel.
6. Write a summary text file containing the per-graph sizes and their average.

The `.result` files are written using the graph filename stem. If the input graph is `example.gpickle`, the corresponding output file is `example.result`. Inside that file, the script iterates over `sorted(graph.nodes())` and writes `1` for vertices in the chosen independent set and `0` otherwise. This makes the output compatible with other tools in the repository that expect solution vectors in this format.

---

## `deg_greedy_result.py` Degree-based Greedy (Deg-greedy)

### Purpose

`deg_greedy_result.py` generates `.result` files using a degree-based greedy heuristic on the residual graph.

### Greedy rule

The script repeatedly:

- selects the current minimum-degree vertex in the remaining graph;
- adds that vertex to the independent set;
- removes the selected vertex and all of its neighbors;
- continues until no vertices remain.

This is a dynamic degree-based rule because degrees are recomputed after each removal. The heuristic therefore adapts to the evolving residual graph rather than relying only on the initial degree ordering.

### Output

For each graph, the script produces:

- a `.result` file encoding the selected independent set;
- a contribution to the summary file listing the size of that set.

The summary text file contains one size per graph and the average size over the folder.

### Typical use

Use `deg_greedy_result.py` when you want a deterministic baseline that produces repository-compatible `.result` files from a simple low-degree greedy construction.

### Command-line arguments

- `--folder_path`: directory containing `.gpickle` graph files.
- `--output_folder`: directory where `.result` files will be saved.
- `--output_file`: text file where the list of solution sizes and their average will be written.
- `--workers`: number of worker processes.

---

## `random_greedy_result.py` Random Greedy (Ran-greedys)

### Purpose

`random_greedy_result.py` generates `.result` files using a random greedy heuristic.

### Greedy rule

The script repeatedly:

- selects a uniformly random vertex from the remaining graph;
- adds that vertex to the independent set;
- removes the selected vertex and all of its neighbors;
- continues until no vertices remain.

Because the next vertex is chosen at random, different runs on the same graph can produce different `.result` files and different independent-set sizes.

### Output

As in `deg_greedy_result.py`, the script writes:

- one `.result` file per input graph;
- one summary text file containing all produced set sizes and their average.

### Typical use

Use `random_greedy_result.py` when you want a stochastic baseline that produces `.result` files in the standard repository format.

### Command-line arguments

- `--folder_path`: directory containing `.gpickle` graph files.
- `--output_folder`: directory where `.result` files will be saved.
- `--output_file`: text file for the per-graph sizes and average size.
- `--workers`: number of worker processes.

---

## Relationship between the two scripts

The scripts differ only in how the next vertex is chosen:

- `deg_greedy_result.py` chooses the current minimum-degree vertex in the residual graph.
- `random_greedy_result.py` chooses a random remaining vertex.

Both then remove that vertex together with its neighbors, continue until the graph is exhausted, and write the selected set in `.result` format.

---

## Notes on interpretation

- The generated `.result` files correspond to heuristic independent sets, not exact MIS solutions.
- `deg_greedy_result.py` is deterministic for a fixed graph.
- `random_greedy_result.py` is stochastic and may produce different outputs across runs.
- These scripts are useful when a downstream pipeline expects `.result` files rather than only summary statistics.

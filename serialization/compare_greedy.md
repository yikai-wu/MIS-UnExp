# Serialization analysis scripts

This note documents three related analysis scripts:

- `compare_greedy.py`
- `compare_greedy_segment.py`
- `compare_greedy_folders.py`

All three scripts are built around the same core question:

> Given a graph and a proposed independent set, how consistent is that solution with a simple degree-based greedy selection process?

More specifically, they repeatedly simulate the following procedure:

1. Start from the nodes selected by the independent-set solution.
2. Among those selected nodes, choose one with minimum current degree in the remaining graph.
3. Break ties randomly.
4. Record the chosen node's degree rank among all remaining nodes.
5. Remove that node and its neighbors.
6. Repeat until no selected nodes remain.

The scripts then summarize how often the selected node was:

- the current minimum-degree node exactly (`rank == 1`);
- within the top 5% lowest-degree remaining nodes;
- within the top 10% lowest-degree remaining nodes.

This provides a way to test whether a solution looks similar to what a degree-based greedy heuristic would produce.

---

## Shared assumptions

All three scripts assume:

- the graph is stored as a NetworkX `.gpickle` file;
- the solution is stored as a text file with one `0` or `1` per line;
- the `1` entries indicate the nodes selected into the independent set;
- node indices in the solution vector match the graph's node ordering.

Each script first validates that the selected nodes form a valid independent set. If two selected nodes are adjacent, the script raises an error instead of continuing.

---

## `compare_greedy.py`

### Purpose

`compare_greedy.py` analyzes a **single graph** and a **single result file**. It is the most focused version of the greedy-consistency analysis and is useful when you want to inspect one instance in detail.

### What it does

- loads one graph from `--graph_file`;
- loads one independent-set vector from `--result_file`;
- validates that the vector represents a valid independent set;
- repeats the randomized greedy ranking procedure `--repeat` times;
- splits each run into the first, second, and last thirds of the selection sequence;
- averages the statistics over all repetitions;
- writes a short text report to `--output_file`.

### Output

The output is a compact text summary showing average statistics for:

- the first third of greedy selections;
- the second third;
- the last third.

For each third, it reports:

- how often the selected node had rank 1;
- how often it was in the top 5%;
- how often it was in the top 10%.

### Typical use

Use this script when you want to examine one graph/result pair and understand whether the independent set resembles the trajectory of a greedy MIS heuristic.

### Command-line arguments

- `--graph_file`: path to one `.gpickle` graph file.
- `--result_file`: path to one `.result`-style vector file.
- `--repeat`: number of randomized tie-breaking repetitions.
- `--output_file`: path to save the text summary.

---

## `compare_greedy_segment.py`

### Purpose

`compare_greedy_segment.py` extends the same analysis to an **entire directory of graphs** matched against a **single directory of result files**.

### What it does

- scans `--graphs_dir` for `.gpickle` files;
- scans `--results_dir` for matching `.result` files;
- matches graph files and result files by filename;
- runs the greedy-consistency analysis for each matched pair;
- repeats the randomized procedure `--repeat` times per graph;
- keeps the repetition with the best fraction of `rank == 1` choices;
- computes overall and segmented statistics for each graph;
- writes both a human-readable text report and a CSV summary.

### Output

This script writes two files into the results directory:

- `ranking.out`: readable per-graph statistics plus overall averages;
- `ranking.csv`: tabular version of the same results.

Each graph entry includes:

- graph filename;
- MIS size;
- proportion of `rank == 1` selections;
- top-5 and top-10 percentages;
- first-, second-, and third-segment statistics.

### Matching behavior

The script matches each graph file to a result file by comparing the basename of the graph file against `.result` filenames in a case-insensitive way. If no match is found, the graph is skipped.

### Typical use

Use this script when you have one experiment folder of solutions and want a per-instance report over the full dataset.

### Command-line arguments

- `--graphs_dir`: directory containing `.gpickle` graph files.
- `--results_dir`: directory containing `.result` files.
- `--repeat`: number of repetitions per graph.
- `--output_file`: optional path for the text report. If omitted, the script writes `ranking.out` in the results directory.

---

## `compare_greedy_folders.py`

### Purpose

`compare_greedy_folders.py` is the batch-orchestration version of the analysis. It processes **multiple result directories** against the same graph directory and aggregates the results across folders.

### What it does

- takes one `--graphs_dir`;
- takes multiple `--results_dirs`;
- runs the same per-graph greedy analysis for each results directory;
- processes result directories in parallel using `ProcessPoolExecutor`;
- writes `ranking.out` and `ranking.csv` inside each results directory;
- collects summary averages for every results directory;
- writes one aggregated summary CSV to `--summary_csv`.

### Output

For each results directory, the script produces:

- `ranking.out`;
- `ranking.csv`.

Across all result directories, it also produces:

- a summary CSV specified by `--summary_csv`.

The summary CSV reports, for each results directory:

- total number of processed graphs;
- average MIS size;
- average proportion of `rank == 1` selections;
- average top-5 and top-10 rates;
- average first-, second-, and third-segment statistics.

### Robustness behavior

If a results directory does not exist, or if no graphs can be processed from it, the script still writes an entry in the summary table, leaving the corresponding fields empty or zero as appropriate. This makes it convenient for comparing multiple experiment folders even when some are missing or incomplete.

### Typical use

Use this script when you want to compare several sets of solver outputs or model outputs on the same graph collection and generate one combined summary table.

### Command-line arguments

- `--graphs_dir`: directory containing `.gpickle` graph files.
- `--results_dirs`: one or more directories containing `.result` files.
- `--repeat`: number of repetitions per graph.
- `--summary_csv`: path to the aggregated summary CSV.

---

## Relationship between the three scripts

The three scripts form a simple progression:

- `compare_greedy.py`: one graph, one result file.
- `compare_greedy_segment.py`: many graphs, one results directory.
- `compare_greedy_folders.py`: many graphs, many results directories.

They use the same underlying greedy idea, but at different scales.

---

## Notes on interpretation

- The randomness comes only from tie-breaking among selected nodes that share the same minimum degree.
- Repeating the procedure is useful because different tie-breaking choices can lead to different ranking sequences.
- In the code, the quantity sometimes described as "1's" or "top 1%" is effectively the proportion of steps where the chosen node had `rank == 1`, meaning it was the current lowest-degree remaining node exactly.
- High values for the `rank == 1`, top-5, or top-10 statistics suggest that the independent set is more consistent with a low-degree greedy construction.

---

## When to use which script

- Use `compare_greedy.py` for manual inspection of one example.
- Use `compare_greedy_segment.py` for a full report on one experiment folder.
- Use `compare_greedy_folders.py` for comparing multiple experiment folders side by side.

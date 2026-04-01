# Local search for independent sets

This note documents `local_search.py`, a local-improvement script for maximum independent set solutions.

The script takes a graph and an initial independent set, then attempts to improve that set using repeated **2-improvement** moves. A 2-improvement removes one vertex from the current independent set and replaces it with two vertices outside the set, provided that the resulting set remains independent. Each successful move increases the size of the independent set by one.

---

## Purpose

`local_search.py` is intended to refine an existing independent-set solution rather than construct one from scratch. It is therefore best viewed as a post-processing step: given an initial solution in `.result` format, the script searches for local improvements that enlarge the solution.

This makes it useful when a separate algorithm has already produced a feasible independent set and one wants a lightweight local search to improve it further.

---

## Input and output

The script expects:

- `--graph_file`: a graph stored as a NetworkX `.gpickle` file;
- `--result_file`: an initial independent set stored as a binary `.result` file, with one `0` or `1` per line;
- `--improved_output`: a file where the improved independent set will be written;
- `--max_iterations`: the maximum number of local-search iterations.

The graph is loaded from the `.gpickle` file, and the initial solution is read by interpreting each line of the `.result` file as a node-membership indicator.

One important detail is that the output file is **not written in the same binary `.result` format as the input**. Instead, the script writes the node IDs of the improved independent set, one per line. This is useful for inspection, but it differs from the repository's standard result-vector format.

---

## Core idea: 2-improvement

The local search is based on a simple neighborhood move. Suppose the current independent set contains a vertex `u`. If one can remove `u` and add two vertices `v1` and `v2` outside the set such that:

- neither `v1` nor `v2` conflicts with the remaining independent set,
- and `v1` and `v2` are not adjacent to each other,

then the set size increases by one. This is called a **2-improvement**.

The script searches for such moves one at a time and applies them iteratively until no further improvement is found or the iteration limit is reached.

---

## Main components

### `read_graph_from_gpickle(file_path)`

Loads the graph from a `.gpickle` file using NetworkX.

### `build_adjacency_list(graph)`

Builds an adjacency-list representation of the graph as a dictionary of sets. This is used to speed up repeated neighbor and edge checks during local search.

### `find_2_improvement(graph_adj_list, independent_set)`

Searches for one valid 2-improvement move. For each vertex currently in the independent set, it examines neighbors outside the set and checks whether two such neighbors can replace the removed vertex without violating independence.

The function:

- iterates through vertices in the current independent set;
- considers neighbors outside the set;
- filters out candidates that conflict with the remaining independent set;
- checks pairs of candidate vertices;
- returns the first valid improved set it finds.

If no valid 2-improvement exists, it returns the original set unchanged.

The implementation also uses random shuffling of candidate neighbors to introduce diversity in the search order.

### `local_search_arw(graph, initial_set, max_iterations=100)`

Runs the iterative local search. It first constructs the adjacency list, then repeatedly calls `find_2_improvement`.

At each iteration:

- if an improvement is found, the current independent set is updated;
- if no improvement is found, the search terminates early.

The search also stops when `max_iterations` has been reached.

---

## Command-line workflow

At runtime, the script performs the following steps:

1. Parse the command-line arguments.
2. Load the graph.
3. Read the initial independent set from the binary `.result` file.
4. Print the size of the initial set.
5. Run local search using repeated 2-improvements.
6. Print the size of the improved set.
7. Write the improved set to the output file.

This makes the script a convenient standalone tool for testing local improvements on a single graph/solution pair.

---

## Interpretation

`local_search.py` is a local refinement method, not an exact solver. If the initial independent set is already locally optimal with respect to 2-improvement moves, the script will return it unchanged. If improving moves are available, the script can increase the solution size step by step.

Because the search order includes randomness when exploring candidate neighbors, different runs may follow different improvement paths, although the script itself is not a large-scale stochastic search procedure.

---

## Typical use

Use `local_search.py` when:

- you already have an initial independent set from another method;
- you want a simple post-processing improvement step;
- you want to test whether 2-improvement local moves can enlarge that solution on a specific graph instance.

If the goal is to process many graph/result pairs at once, `local_search_batch.py` is the batch-processing counterpart. If the goal is to inspect iteration-wise statistics such as the number of available 2-improvements, `local_search_stats.py` is the more instrumented version.

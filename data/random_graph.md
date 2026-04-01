# Random graph generation (`random_graph.py`)

We use the MIS benchmark framework from previous work as the base and add several extra random graph generators on top of it.  
The original framework already provides a common sampling interface and dataset-writing logic; this file extends that with additional graph families (especially fixed-size variants and sorted-output variants) for controlled MIS experiments.

This documentation is written so that it can also be used directly in the upstream [MIS benchmark framework repository](https://github.com/MaxiBoether/mis-benchmark-framework) by replacing that repository's `random_graph.md` with this version.

At a high level:

- `GraphSampler` subclasses define *how one random graph is sampled*.
- `RandomGraphGenerator` defines *how many samples are generated and how each one is saved/labeled*.

---

## Abstract base class

### `GraphSampler`

- **`generate_graph()`**: abstract method implemented by each sampler subclass. It defines the common interface for producing a single `networkx.Graph` instance from the sampler's parameters.

---

## Samplers from MIS benchmark

These classes follow the same pattern: set parameters in `__init__`, expose a short ID string in `__str__`, and generate one random graph in `generate_graph`.

### `ErdosRenyi`

- **`__init__(min_n, max_n, p)`**: stores the node-count range and edge probability for an Erdős-Rényi model. For each sample, the number of vertices is drawn uniformly from `[min_n, max_n]`, and each possible edge is included independently with probability `p`.
- **`__str__()`**: returns the identifier `ER_{min_n}_{max_n}_{p}`, which is used when naming generated instances.
- **`generate_graph()`**: samples `n` uniformly from `[min_n, max_n]` and returns `nx.erdos_renyi_graph(n, p)`. The resulting graph is an unstructured random graph with approximately homogeneous connectivity and no explicit hub mechanism.

### `GNM`

- **`__init__(min_n, max_n, m)`**: stores the node-count range and the fixed number of edges `m` for a Erdos-Renyi `G(n,m)` model. Each sample uses a random number of vertices in `[min_n, max_n]`.
- **`__str__()`**: returns `GNM_{min_n}_{max_n}_{m}`.
- **`generate_graph()`**: samples `n` uniformly from `[min_n, max_n]` and returns `nx.gnm_random_graph(n, m)`. This produces a graph with exactly `m` edges, chosen uniformly from all possible edge sets on `n` vertices.

### `BarabasiAlbert`

- **`__init__(min_n, max_n, m)`**: stores the size range and attachment parameter for a Barabási-Albert preferential-attachment model. New vertices connect to existing vertices with probability biased toward high-degree nodes.
- **`__str__()`**: returns `BA_{min_n}_{max_n}_{m}`.
- **`generate_graph()`**: samples `n` uniformly from `[min_n, max_n]` and returns `nx.barabasi_albert_graph(n, min(m, n))`. The generated graph typically exhibits hub formation and a heavy-tailed degree distribution.

### `HolmeKim`

- **`__init__(min_n, max_n, m, p)`**: stores the size range, attachment parameter, and triangle-formation probability for the Holme-Kim model. This model augments preferential attachment with an explicit mechanism for closing triangles.
- **`__str__()`**: returns `HK_{min_n}_{max_n}_{m}_{p}`.
- **`generate_graph()`**: samples `n` uniformly from `[min_n, max_n]` and returns `nx.powerlaw_cluster_graph(n, min(m, n), p)`. The resulting graph combines scale-free degree behavior with higher local clustering than standard Barabási-Albert graphs.

### `WattsStrogatz`

- **`__init__(min_n, max_n, k, p)`**: stores the size range, local neighborhood size `k`, and rewiring probability `p` for the Watts-Strogatz small-world model.
- **`__str__()`**: returns `WS_{min_n}_{max_n}_{k}_{p}`.
- **`generate_graph()`**: samples `n` uniformly from `[min_n, max_n]` and returns `nx.watts_strogatz_graph(n, k, p)`. The graph begins from a ring-lattice structure and rewires a fraction of edges, producing short path lengths while preserving substantial local connectivity.

### `HyperbolicRandomGraph`

- **`__init__(min_n, max_n, alpha, t, degree, threads)`**:
- stores the hyperbolic random graph parameters and the node-count range;
- checks whether the external `girgs` implementation is available under `data_generation/girgs`;
- if the repository is missing, clones [chistopher/girgs](https://github.com/chistopher/girgs), checks out the pinned commit, creates a build directory, and compiles the `genhrg` binary.
- **`__str__()`**: returns `HRG_{min_n}_{max_n}_{alpha}_{t}_{degree}`.
- **`generate_graph()`**:
  - samples `n` uniformly from `[min_n, max_n]`;
  - executes `genhrg` with the configured hyperbolic parameters;
  - parses the temporary edge-list output;
  - constructs and returns a `networkx` graph with `n` vertices and the sampled edges.
  This model is intended to generate graphs with strong clustering and heavy-tailed degree distributions, which are often used to approximate real-world complex networks more closely than purely uniform random models.

### `RandomGraphGenerator`

- **`__init__(output_path, graph_sampler, num_graphs=1)`**: configures a dataset-generation job with an output directory, a `GraphSampler` instance, and the number of graph samples to produce.
- **`generate(gen_labels=False, weighted=False)`**:
  - iterates `num_graphs` times;
  - generates one graph per iteration by calling `graph_sampler.generate_graph()`;
  - optionally assigns integer node weights using `random_weight` from `DataGenerator`;
  - optionally computes MIS labels with Gurobi and stores them as node attributes;
  - serializes each graph to a `.gpickle` file.
  In effect, this class turns a graph sampler into a reusable dataset writer for supervised or weighted MIS experiments.

---

## Additional samplers added in this codebase

These additions are useful when you want fixed-size instances and stable serialized output order.

### `GND`

- **`__init__(n, d)`**: stores a fixed number of vertices `n` and a target average degree `d`. The implementation converts this average degree into an edge count using `m = n*d/2`.
- **`__str__()`**: returns `GND_{n}_{d}`.
- **`generate_graph()`**: computes `m = n*d/2` and returns `nx.gnm_random_graph(n, m)`. The result is a fixed-size `G(n,m)` graph whose expected average degree is approximately `d`.

### `Regular`

- **`__init__(n, d)`**: stores the graph size and the regular degree. Every sampled graph is required to have exactly degree `d` at every vertex.
- **`__str__()`**: returns `Reg_{n}_{d}`.
- **`generate_graph()`**:
  - samples a graph with `nx.random_regular_graph(d, n)`;
  - rebuilds the graph with sorted nodes and sorted edges before returning it.
  The reordering step does not change the graph structure; it only stabilizes serialization order across saved instances.

### `BA_n_m`

- **`__init__(n, m)`**: stores a fixed graph size and Barabási-Albert attachment parameter.
- **`__str__()`**: returns `BA_{n}_{m}`.
- **`generate_graph()`**: returns a fixed-size preferential-attachment graph from `nx.barabasi_albert_graph(n, m)`, then copies it into a graph with sorted nodes and edges. The underlying model favors hub formation and produces non-uniform degree structure.

### `HK_n_m_p`

- **`__init__(n, m, p)`**: stores a fixed graph size together with the Holme-Kim attachment and triangle-formation parameters.
- **`__str__()`**: returns `HK_{n}_{m}` (`p` is not included in the tag string).
- **`generate_graph()`**: returns a fixed-size Holme-Kim graph from `nx.powerlaw_cluster_graph(n, m, p)`, then rebuilds it with sorted nodes and edges. The sampled graphs combine power-law-like hubs with stronger local clustering than standard preferential-attachment graphs.

### `WS_n_k_p`

- **`__init__(n, k, p)`**: stores a fixed graph size and the parameters of the Watts-Strogatz small-world model.
- **`__str__()`**: returns `WS_{n}_{k}` (`p` is not included in the tag string).
- **`generate_graph()`**: returns a fixed-size small-world graph from `nx.watts_strogatz_graph(n, k, p)`, then rebuilds it with sorted nodes and edges. The resulting graphs preserve local neighborhood structure while introducing a tunable number of long-range shortcuts.

---

## Related dependencies

- `networkx`: random graph constructors and graph object handling.
- `DataGenerator` (from `generator.py`): provides `random_weight` and `_call_gurobi_solver`.
- `run_command_with_live_output` (from `utils`): used to run external HRG binary commands.

# `evaluate.py` Description (with Degree-Based Greedy Comparison for LTFT (GFlowNets))

## What this script does

`evaluate.py` runs inference for a trained GFlowNet policy on a test set of graphs (MIS task), writes prediction files, and reports quality statistics.

At a high level it:

1. Loads config and model checkpoint.
2. Builds test batches.
3. Runs repeated stochastic rollouts per graph (`num_repeat = 20`).
4. Saves best found MIS assignment per graph as `.result`.
5. Logs ranking diagnostics (`rankings.out`) and aggregate percentages (`stats.out`).

---

## Where the degree-based greedy comparison happens

The comparison is not in this file directly; `evaluate.py` calls:

- `env.step_with_ranking(action)`

Inside `gflownet/util.py`, `step_with_ranking` computes:

- `rankings, ranking_stats = self.degree_ranking(action, state)`

before applying the chosen action.

So each model action is compared against a **degree-based ordering** of currently valid nodes (nodes with state `2`, i.e., undecided).

---

## What "degree-based greedy" means here

For each graph step:

- Build the subgraph induced by undecided nodes.
- Compute node degrees in that subgraph.
- Rank the model's selected node by degree.

Current ranking rule in `degree_ranking`:

- `rank = (#nodes with strictly smaller degree than selected node) + 1`

Implication:

- `rank = 1` means the model picked a node with the **minimum degree** among undecided nodes.
- This is a **degree-priority comparison signal**, not a separate greedy solver run.

---

## Metrics written by `evaluate.py` from that comparison

During rollout, each step accumulates:

- `rank1`: percent of valid graphs where selected node is rank 1.
- `top5%`: percent where selected node rank is within top 5% (at least one node).
- `top10%`: percent where selected node rank is within top 10% (at least one node).

At the end, these are averaged over all rollout steps and written to:

- `stats.out`

and raw per-step rank lists are written to:

- `rankings.out`

---

## Relation to final MIS quality

The degree-ranking stats evaluate **action alignment** with a degree heuristic.
They are different from MIS size quality metrics:

- MIS size mean/std (`mis_ls`, `mis_top20_ls`)
- Log-reward summaries
- Final `.result` vectors (best across repeats)

You can think of it as:

- **Behavioral metric**: "How similar are chosen actions to degree-priority choices?"
- **Outcome metric**: "How large is the resulting independent set?"

---

## Important nuance

Because ranking is computed from degree order only, high `rank1/top5/top10` means the policy often matches that degree criterion. It does **not** automatically imply best MIS size, and low agreement does not necessarily mean poor final solutions. The script intentionally reports both behavior-level and outcome-level signals.


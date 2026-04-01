import argparse
import random
import networkx as nx
import numpy as np

def is_valid_independent_set(G, independent_set):
    """
    Check if the provided set is a valid independent set.
    An independent set contains no two adjacent nodes.
    """
    for node in independent_set:
        for neighbor in G.neighbors(node):
            if neighbor in independent_set:
                return False
    return True

def run_procedure(G, independent_set_vector):
    """
    Run the degree-based greedy procedure to analyze the independent set.
    During the process, store rankings, top 5% flags, and top 10% flags for segmentation.
    """
    n = len(G.nodes)
    
    # Validate the dimension of the vector
    if len(independent_set_vector) != n:
        raise ValueError("The dimension of the vector does not match the number of nodes in the graph.")
    
    # Initialize the independent set I
    I = {node for node, in_set in enumerate(independent_set_vector) if in_set == 1}
    rankings = []  # To store the rankings of selected nodes
    top_5_percent_flags = []  # Whether each rank is in the top 5%
    top_10_percent_flags = []  # Whether each rank is in the top 10%

    while I:
        # Compute degrees dynamically for all nodes in I
        degrees = {v: G.degree[v] for v in I}

        # Find the node(s) with the lowest degree
        min_degree = min(degrees.values())
        candidates = [v for v, degree in degrees.items() if degree == min_degree]

        # Randomly select one candidate (break ties randomly)
        v = random.choice(candidates)

        # Calculate rank dynamically based on the current degree distribution
        current_degrees = [G.degree[node] for node in G.nodes]
        rank = sum(1 for degree in current_degrees if degree < G.degree[v]) + 1
        rankings.append(rank)

        # Compute thresholds for top 5% and top 10% based on remaining nodes
        remaining_nodes = len(G.nodes)
        top_5_threshold = max(int(0.05 * remaining_nodes), 1)  # Ensure at least 1 node qualifies
        top_10_threshold = max(int(0.10 * remaining_nodes), 1)  # Ensure at least 1 node qualifies

        # Record flags for top 5% and top 10%
        top_5_percent_flags.append(rank <= top_5_threshold)
        top_10_percent_flags.append(rank <= top_10_threshold)

        # Remove the selected node and its neighbors from the graph
        neighbors = list(G.neighbors(v))
        nodes_to_remove = neighbors + [v]
        G.remove_nodes_from(nodes_to_remove)

        # Remove the selected node from the independent set
        I.discard(v)

    return rankings, top_5_percent_flags, top_10_percent_flags

def compute_segmented_stats(rankings, top_5_percent_flags, top_10_percent_flags):
    """
    Compute statistics for the first, second, and last thirds of the rankings.
    """
    # Determine the size of each segment
    total_count = len(rankings)
    segment_size = total_count // 3

    # Split the data into segments
    first_third = slice(0, segment_size)
    second_third = slice(segment_size, 2 * segment_size)
    last_third = slice(2 * segment_size, total_count)

    # Compute stats for each segment
    def compute_stats(segment):
        segment_length = len(rankings[segment])
        if segment_length == 0:
            return {"top_1%": 0.0, "top_5%": 0.0, "top_10%": 0.0}
        
        top_1_percentage = rankings[segment].count(1) / segment_length * 100
        top_5_percentage = sum(top_5_percent_flags[segment]) / segment_length * 100
        top_10_percentage = sum(top_10_percent_flags[segment]) / segment_length * 100

        return {
            "top_1%": top_1_percentage,
            "top_5%": top_5_percentage,
            "top_10%": top_10_percentage,
        }

    return {
        "first_third": compute_stats(first_third),
        "second_third": compute_stats(second_third),
        "last_third": compute_stats(last_third),
    }

def main(graph_file, result_file, repeat, output_file):
    # Load the graph from the gpickle file
    original_G = nx.read_gpickle(graph_file)
    
    # Load the independent set vector
    with open(result_file, 'r') as f:
        independent_set_vector = np.array([int(line.strip()) for line in f])

    # Validate if the result_file represents a valid independent set
    independent_set = {node for node, in_set in enumerate(independent_set_vector) if in_set == 1}
    if not is_valid_independent_set(original_G, independent_set):
        raise ValueError("The result file does not represent a valid independent set.")

    # Repeat the procedure for the specified number of times
    all_rankings = []
    all_top_5_flags = []
    all_top_10_flags = []
    for _ in range(repeat):
        # Create a fresh copy of the graph for each iteration
        G = original_G.copy()
        rankings, top_5_flags, top_10_flags = run_procedure(G, independent_set_vector)
        all_rankings.append(rankings)
        all_top_5_flags.append(top_5_flags)
        all_top_10_flags.append(top_10_flags)

    # Compute average stats for each segment (first, second, last thirds) over all runs
    avg_first_third = {"top_1%": 0.0, "top_5%": 0.0, "top_10%": 0.0}
    avg_second_third = {"top_1%": 0.0, "top_5%": 0.0, "top_10%": 0.0}
    avg_last_third = {"top_1%": 0.0, "top_5%": 0.0, "top_10%": 0.0}

    # Accumulate stats for each segment
    for i in range(repeat):
        segmented_stats = compute_segmented_stats(all_rankings[i], all_top_5_flags[i], all_top_10_flags[i])
        avg_first_third["top_1%"] += segmented_stats["first_third"]["top_1%"]
        avg_first_third["top_5%"] += segmented_stats["first_third"]["top_5%"]
        avg_first_third["top_10%"] += segmented_stats["first_third"]["top_10%"]

        avg_second_third["top_1%"] += segmented_stats["second_third"]["top_1%"]
        avg_second_third["top_5%"] += segmented_stats["second_third"]["top_5%"]
        avg_second_third["top_10%"] += segmented_stats["second_third"]["top_10%"]

        avg_last_third["top_1%"] += segmented_stats["last_third"]["top_1%"]
        avg_last_third["top_5%"] += segmented_stats["last_third"]["top_5%"]
        avg_last_third["top_10%"] += segmented_stats["last_third"]["top_10%"]

    # Compute the average for each segment
    avg_first_third = {key: value / repeat for key, value in avg_first_third.items()}
    avg_second_third = {key: value / repeat for key, value in avg_second_third.items()}
    avg_last_third = {key: value / repeat for key, value in avg_last_third.items()}

    # Prepare the output results
    result_str = (
        f"Average Stats over {repeat} runs:\n"
        f"  First Third: {avg_first_third}\n"
        f"  Second Third: {avg_second_third}\n"
        f"  Last Third: {avg_last_third}\n"
    )

    # Print the results to the console
    print(result_str)

    # Save to the output file
    with open(output_file, 'w') as f:
        f.write(result_str)

    print("Results saved to:", output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check if an independent set is generated by a degree-based greedy algorithm with repetitions.")
    parser.add_argument("--graph_file", required=True, help="Path to the gpickle file containing the graph.")
    parser.add_argument("--result_file", required=True, help="Path to the file containing the n-vector.")
    parser.add_argument("--repeat", type=int, required=True, help="Number of times to repeat the procedure.")
    parser.add_argument("--output_file", required=True, help="Path to save the result file.")
    args = parser.parse_args()
    
    main(args.graph_file, args.result_file, args.repeat, args.output_file)

import argparse
import random
import networkx as nx
import numpy as np
import os
import glob
import csv
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial


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
    total_count = len(rankings)
    if total_count == 0:
        return {
            "first_third": {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0},
            "second_third": {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0},
            "last_third": {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0},
        }
    
    segment_size = total_count // 3

    first_third = slice(0, segment_size)
    second_third = slice(segment_size, 2 * segment_size)
    last_third = slice(2 * segment_size, total_count)

    def compute_stats(segment):
        segment_length = len(rankings[segment])
        if segment_length == 0:
            return {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0}
        
        rank_1_proportion = rankings[segment].count(1) / segment_length * 100
        top_5_proportion = sum(top_5_percent_flags[segment]) / segment_length * 100
        top_10_proportion = sum(top_10_percent_flags[segment]) / segment_length * 100

        return {
            "rank_1": rank_1_proportion,
            "top_5": top_5_proportion,
            "top_10": top_10_proportion,
        }

    return {
        "first_third": compute_stats(first_third),
        "second_third": compute_stats(second_third),
        "last_third": compute_stats(last_third),
    }


def find_matching_result_file(graph_file, results_dir):
    """
    Find the result file in the results directory that matches the graph file name (case-insensitive).
    """
    graph_name = os.path.splitext(os.path.basename(graph_file))[0].lower()  # Normalize to lowercase
    result_files = glob.glob(os.path.join(results_dir, "*.result"))

    for result_file in result_files:
        result_name = os.path.splitext(os.path.basename(result_file))[0].lower()  # Normalize to lowercase
        if graph_name in result_name:
            return result_file

    return None


def process_single_graph(graph_file, result_file, repeat):
    """
    Process a single graph and its corresponding result file.
    """
    original_G = nx.read_gpickle(graph_file)
    with open(result_file, 'r') as f:
        independent_set_vector = np.array([int(line.strip()) for line in f])

    independent_set = {node for node, in_set in enumerate(independent_set_vector) if in_set == 1}
    if not is_valid_independent_set(original_G, independent_set):
        raise ValueError(f"The result file {result_file} does not represent a valid independent set.")

    best_ranking = None
    best_top_5_flags = []
    best_top_10_flags = []
    best_ratio = 0.0

    for _ in range(repeat):
        G = original_G.copy()
        ranking, top_5_flags, top_10_flags = run_procedure(G, independent_set_vector)

        num_ones = ranking.count(1)
        proportion_of_ones = num_ones / len(ranking) if len(ranking) > 0 else 0

        if proportion_of_ones > best_ratio:
            best_ratio = proportion_of_ones
            best_ranking = ranking
            best_top_5_flags = top_5_flags
            best_top_10_flags = top_10_flags

    segmented_stats = compute_segmented_stats(best_ranking, best_top_5_flags, best_top_10_flags)

    total_count = len(best_ranking)
    top_5_percentage = sum(best_top_5_flags) / total_count * 100 if total_count > 0 else 0.0
    top_10_percentage = sum(best_top_10_flags) / total_count * 100 if total_count > 0 else 0.0

    return {
        "graph_file": os.path.basename(graph_file),
        "mis_size": int(independent_set_vector.sum()),
        "best_ratio": best_ratio * 100,
        "top_5_percentage": top_5_percentage,
        "top_10_percentage": top_10_percentage,
        "segmented_stats": segmented_stats,
    }


def write_csv(stats_list, cumulative_stats, total_graphs, csv_file):
    """
    Write the results to a CSV file with concise labels.
    """
    header = [
        "Graph",
        "MIS Size",
        "Prop 1's",
        "Top 5",
        "Top 10",
        "1st Third 1's",
        "1st Third Top 5",
        "1st Third Top 10",
        "2nd Third 1's",
        "2nd Third Top 5",
        "2nd Third Top 10",
        "3rd Third 1's",
        "3rd Third Top 5",
        "3rd Third Top 10",
    ]

    with open(csv_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)

        # Write individual graph stats
        for stats in stats_list:
            writer.writerow([
                stats["graph_file"],
                stats["mis_size"],
                f"{stats['best_ratio']:.2f}",
                f"{stats['top_5_percentage']:.2f}",
                f"{stats['top_10_percentage']:.2f}",
                f"{stats['segmented_stats']['first_third']['rank_1']:.2f}",
                f"{stats['segmented_stats']['first_third']['top_5']:.2f}",
                f"{stats['segmented_stats']['first_third']['top_10']:.2f}",
                f"{stats['segmented_stats']['second_third']['rank_1']:.2f}",
                f"{stats['segmented_stats']['second_third']['top_5']:.2f}",
                f"{stats['segmented_stats']['second_third']['top_10']:.2f}",
                f"{stats['segmented_stats']['last_third']['rank_1']:.2f}",
                f"{stats['segmented_stats']['last_third']['top_5']:.2f}",
                f"{stats['segmented_stats']['last_third']['top_10']:.2f}",
            ])

        if total_graphs > 0:
            # Write averages
            writer.writerow([
                "Average",
                f"{cumulative_stats['mis_size'] / total_graphs:.2f}",
                f"{cumulative_stats['best_ratio'] / total_graphs:.2f}",
                f"{cumulative_stats['top_5_percentage'] / total_graphs:.2f}",
                f"{cumulative_stats['top_10_percentage'] / total_graphs:.2f}",
                f"{cumulative_stats['first_third']['rank_1'] / total_graphs:.2f}",
                f"{cumulative_stats['first_third']['top_5'] / total_graphs:.2f}",
                f"{cumulative_stats['first_third']['top_10'] / total_graphs:.2f}",
                f"{cumulative_stats['second_third']['rank_1'] / total_graphs:.2f}",
                f"{cumulative_stats['second_third']['top_5'] / total_graphs:.2f}",
                f"{cumulative_stats['second_third']['top_10'] / total_graphs:.2f}",
                f"{cumulative_stats['last_third']['rank_1'] / total_graphs:.2f}",
                f"{cumulative_stats['last_third']['top_5'] / total_graphs:.2f}",
                f"{cumulative_stats['last_third']['top_10'] / total_graphs:.2f}",
            ])


def process_results_dir(results_dir, graphs_dir, repeat, header_keys):
    """
    Process all graphs in graphs_dir against a single results_dir.
    Saves output and CSV within the results_dir and returns summary statistics.
    If results_dir does not exist, returns a summary_entry with empty fields.
    """
    summary_entry = {
        "Results Directory": results_dir,
        "Total Graphs": 0,
        "Average MIS Size": "",
        "Average Prop 1's": "",
        "Average Top 5": "",
        "Average Top 10": "",
        "1st Third 1's": "",
        "1st Third Top 5": "",
        "1st Third Top 10": "",
        "2nd Third 1's": "",
        "2nd Third Top 5": "",
        "2nd Third Top 10": "",
        "3rd Third 1's": "",
        "3rd Third Top 5": "",
        "3rd Third Top 10": "",
    }

    if not os.path.isdir(results_dir):
        # Directory does not exist; return summary_entry with empty fields
        print(f"[INFO] Results directory '{results_dir}' does not exist. Leaving corresponding row empty.")
        return summary_entry

    output_file = os.path.join(results_dir, "ranking.out")
    csv_file = os.path.join(results_dir, "ranking.csv")

    total_graphs = 0
    cumulative_stats = {
        "mis_size": 0,
        "best_ratio": 0.0,
        "top_5_percentage": 0.0,
        "top_10_percentage": 0.0,
        "first_third": {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0},
        "second_third": {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0},
        "last_third": {"rank_1": 0.0, "top_5": 0.0, "top_10": 0.0},
    }

    stats_list = []

    try:
        with open(output_file, 'w') as out_f:
            graph_files = glob.glob(os.path.join(graphs_dir, "*.gpickle"))

            for graph_file in graph_files:
                result_file = find_matching_result_file(graph_file, results_dir)
                if not result_file:
                    out_f.write(f"No matching result file for {os.path.basename(graph_file)}. Skipping...\n\n")
                    continue

                try:
                    stats = process_single_graph(graph_file, result_file, repeat)
                except ValueError as e:
                    out_f.write(f"Error processing {os.path.basename(graph_file)} with {os.path.basename(result_file)}: {e}\n\n")
                    continue

                out_f.write(f"Graph: {stats['graph_file']}\n")
                out_f.write(f"  MIS Size: {stats['mis_size']}\n")
                out_f.write(f"  Prop 1's: {stats['best_ratio']:.2f}\n")
                out_f.write(f"  Top 5: {stats['top_5_percentage']:.2f}\n")
                out_f.write(f"  Top 10: {stats['top_10_percentage']:.2f}\n")
                out_f.write(f"  Segmented Stats:\n")
                out_f.write(f"    1st Third 1's: {stats['segmented_stats']['first_third']['rank_1']:.2f}\n")
                out_f.write(f"    1st Third Top 5: {stats['segmented_stats']['first_third']['top_5']:.2f}\n")
                out_f.write(f"    1st Third Top 10: {stats['segmented_stats']['first_third']['top_10']:.2f}\n")
                out_f.write(f"    2nd Third 1's: {stats['segmented_stats']['second_third']['rank_1']:.2f}\n")
                out_f.write(f"    2nd Third Top 5: {stats['segmented_stats']['second_third']['top_5']:.2f}\n")
                out_f.write(f"    2nd Third Top 10: {stats['segmented_stats']['second_third']['top_10']:.2f}\n")
                out_f.write(f"    3rd Third 1's: {stats['segmented_stats']['last_third']['rank_1']:.2f}\n")
                out_f.write(f"    3rd Third Top 5: {stats['segmented_stats']['last_third']['top_5']:.2f}\n")
                out_f.write(f"    3rd Third Top 10: {stats['segmented_stats']['last_third']['top_10']:.2f}\n\n")

                total_graphs += 1
                cumulative_stats["mis_size"] += stats["mis_size"]
                cumulative_stats["best_ratio"] += stats["best_ratio"]
                cumulative_stats["top_5_percentage"] += stats["top_5_percentage"]
                cumulative_stats["top_10_percentage"] += stats["top_10_percentage"]

                for segment in ["first_third", "second_third", "last_third"]:
                    for key in cumulative_stats[segment]:
                        cumulative_stats[segment][key] += stats["segmented_stats"][segment][key]

                stats_list.append(stats)

            write_csv(stats_list, cumulative_stats, total_graphs, csv_file)

            # Write summary averages to output file
            if total_graphs > 0:
                out_f.write("Summary Averages Across All Graphs:\n")
                out_f.write(f"  Average MIS Size: {cumulative_stats['mis_size'] / total_graphs:.2f}\n")
                out_f.write(f"  Average Prop 1's: {cumulative_stats['best_ratio'] / total_graphs:.2f}\n")
                out_f.write(f"  Average Top 5: {cumulative_stats['top_5_percentage'] / total_graphs:.2f}\n")
                out_f.write(f"  Average Top 10: {cumulative_stats['top_10_percentage'] / total_graphs:.2f}\n")
                out_f.write(f"  Segmented Stats Averages:\n")
                out_f.write(f"    1st Third 1's: {cumulative_stats['first_third']['rank_1'] / total_graphs:.2f}\n")
                out_f.write(f"    1st Third Top 5: {cumulative_stats['first_third']['top_5'] / total_graphs:.2f}\n")
                out_f.write(f"    1st Third Top 10: {cumulative_stats['first_third']['top_10'] / total_graphs:.2f}\n")
                out_f.write(f"    2nd Third 1's: {cumulative_stats['second_third']['rank_1'] / total_graphs:.2f}\n")
                out_f.write(f"    2nd Third Top 5: {cumulative_stats['second_third']['top_5'] / total_graphs:.2f}\n")
                out_f.write(f"    2nd Third Top 10: {cumulative_stats['second_third']['top_10'] / total_graphs:.2f}\n")
                out_f.write(f"    3rd Third 1's: {cumulative_stats['last_third']['rank_1'] / total_graphs:.2f}\n")
                out_f.write(f"    3rd Third Top 5: {cumulative_stats['last_third']['top_5'] / total_graphs:.2f}\n")
                out_f.write(f"    3rd Third Top 10: {cumulative_stats['last_third']['top_10'] / total_graphs:.2f}\n")
            else:
                out_f.write("No graphs were processed.\n")

        # Prepare summary data for this results_dir
        if total_graphs > 0:
            summary_entry.update({
                "Total Graphs": total_graphs,
                "Average MIS Size": cumulative_stats["mis_size"] / total_graphs,
                "Average Prop 1's": cumulative_stats["best_ratio"] / total_graphs,
                "Average Top 5": cumulative_stats["top_5_percentage"] / total_graphs,
                "Average Top 10": cumulative_stats["top_10_percentage"] / total_graphs,
                "1st Third 1's": cumulative_stats["first_third"]["rank_1"] / total_graphs,
                "1st Third Top 5": cumulative_stats["first_third"]["top_5"] / total_graphs,
                "1st Third Top 10": cumulative_stats["first_third"]["top_10"] / total_graphs,
                "2nd Third 1's": cumulative_stats["second_third"]["rank_1"] / total_graphs,
                "2nd Third Top 5": cumulative_stats["second_third"]["top_5"] / total_graphs,
                "2nd Third Top 10": cumulative_stats["second_third"]["top_10"] / total_graphs,
                "3rd Third 1's": cumulative_stats["last_third"]["rank_1"] / total_graphs,
                "3rd Third Top 5": cumulative_stats["last_third"]["top_5"] / total_graphs,
                "3rd Third Top 10": cumulative_stats["last_third"]["top_10"] / total_graphs,
            })
        else:
            # No graphs processed; summary_entry already has default values
            pass

    except Exception as e:
        print(f"[ERROR] An exception occurred while processing '{results_dir}': {e}")
        # Leave summary_entry with default empty fields
        pass

    return summary_entry


def write_summary_csv(summary_data, summary_csv, results_dirs):
    """
    Write the aggregated summary statistics to a summary CSV file.
    Ensures the order of results_dirs is maintained.
    """
    if not summary_data:
        print("No summary data to write.")
        return

    # Define the header explicitly to ensure consistency
    header = [
        "Results Directory",
        "Total Graphs",
        "Average MIS Size",
        "Average Prop 1's",
        "Average Top 5",
        "Average Top 10",
        "1st Third 1's",
        "1st Third Top 5",
        "1st Third Top 10",
        "2nd Third 1's",
        "2nd Third Top 5",
        "2nd Third Top 10",
        "3rd Third 1's",
        "3rd Third Top 5",
        "3rd Third Top 10",
    ]

    # Create a mapping from results_dir to summary_entry
    summary_dict = {entry["Results Directory"]: entry for entry in summary_data}

    with open(summary_csv, "w", newline="") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=header)
        writer.writeheader()
        for results_dir in results_dirs:
            entry = summary_dict.get(results_dir)
            if entry:
                writer.writerow(entry)
            else:
                # This should not happen as all results_dirs are processed
                # But in case, write an empty row
                empty_entry = {key: "" for key in header}
                empty_entry["Results Directory"] = results_dir
                writer.writerow(empty_entry)


def main(graphs_dir, results_dirs, repeat, summary_csv):
    """
    Main function to orchestrate parallel processing of multiple results_dirs.
    """
    summary_data = []

    # Define the header keys
    header_keys = [
        "Results Directory",
        "Total Graphs",
        "Average MIS Size",
        "Average Prop 1's",
        "Average Top 5",
        "Average Top 10",
        "1st Third 1's",
        "1st Third Top 5",
        "1st Third Top 10",
        "2nd Third 1's",
        "2nd Third Top 5",
        "2nd Third Top 10",
        "3rd Third 1's",
        "3rd Third Top 5",
        "3rd Third Top 10",
    ]

    # Submit all results_dirs to the executor regardless of existence
    num_workers = min(len(results_dirs), os.cpu_count() or 1)

    print(f"[INFO] Starting parallel processing with {num_workers} worker(s)...")

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Create a partial function with fixed graphs_dir and repeat
        process_func = partial(process_results_dir, graphs_dir=graphs_dir, repeat=repeat, header_keys=header_keys)

        # Submit all results_dirs to the executor
        future_to_results_dir = {executor.submit(process_func, results_dir): results_dir for results_dir in results_dirs}

        for future in as_completed(future_to_results_dir):
            results_dir = future_to_results_dir[future]
            try:
                summary_entry = future.result()
                if summary_entry:
                    summary_data.append(summary_entry)
                    if summary_entry["Total Graphs"] > 0:
                        print(f"[SUCCESS] Processed '{results_dir}' with {summary_entry['Total Graphs']} graph(s).")
                    else:
                        print(f"[INFO] '{results_dir}' exists but no graphs were processed.")
                else:
                    # This should not happen as process_results_dir always returns a summary_entry
                    print(f"[WARNING] No summary data for '{results_dir}'.")
            except Exception as exc:
                print(f"[EXCEPTION] '{results_dir}' generated an exception: {exc}")
                # Create an empty summary_entry for this results_dir
                empty_entry = {
                    "Results Directory": results_dir,
                    "Total Graphs": 0,
                    "Average MIS Size": "",
                    "Average Prop 1's": "",
                    "Average Top 5": "",
                    "Average Top 10": "",
                    "1st Third 1's": "",
                    "1st Third Top 5": "",
                    "1st Third Top 10": "",
                    "2nd Third 1's": "",
                    "2nd Third Top 5": "",
                    "2nd Third Top 10": "",
                    "3rd Third 1's": "",
                    "3rd Third Top 5": "",
                    "3rd Third Top 10": "",
                }
                summary_data.append(empty_entry)

    # Write the aggregated summary CSV in the order of results_dirs
    write_summary_csv(summary_data, summary_csv, results_dirs)

    print(f"[INFO] Summary CSV saved to: {summary_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the degree-based greedy analysis for multiple graphs and multiple result directories in parallel.")
    parser.add_argument("--graphs_dir", required=True, help="Path to the directory containing graph files (.gpickle).")
    parser.add_argument("--results_dirs", required=True, nargs='+', help="Paths to the directories containing result files (.result). Provide one or more directories separated by space.")
    parser.add_argument("--repeat", type=int, required=True, help="Number of repetitions for each graph.")
    parser.add_argument("--summary_csv", required=True, help="Path to save the aggregated summary CSV file.")
    args = parser.parse_args()
    
    main(args.graphs_dir, args.results_dirs, args.repeat, args.summary_csv)

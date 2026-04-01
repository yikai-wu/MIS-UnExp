import os
import random
import networkx as nx
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

def maximum_independent_set_random(graph):
    # Create a copy of the graph to avoid modifying the original graph
    temp_graph = graph.copy()
    independent_set = set()
    
    while len(temp_graph) > 0:
        # Pick a random node from the graph
        node = random.choice(list(temp_graph.nodes()))  # Select a random node
        
        # Add this node to the independent set
        independent_set.add(node)
        
        # Remove this node and all its neighbors from the graph
        neighbors = list(temp_graph.neighbors(node))
        temp_graph.remove_node(node)
        temp_graph.remove_nodes_from(neighbors)
    
    return independent_set

def process_graph_file(graph_path, output_folder):
    # Load the graph from the gpickle file
    graph = nx.read_gpickle(graph_path)
    
    # Compute the maximum independent set using random selection
    independent_set = maximum_independent_set_random(graph)
    
    # Write the independent set to the output file
    write_independent_set_to_file(graph, independent_set, graph_path, output_folder)
    
    return len(independent_set)

def write_independent_set_to_file(graph, independent_set, graph_path, output_folder):
    # Use pathlib.Path to get the stem of the file name
    graph_filename_stem = Path(graph_path).stem
    result_filename = f"{graph_filename_stem}.result"
    result_file_path = os.path.join(output_folder, result_filename)
    
    # Write the independent set to the file
    with open(result_file_path, 'w') as file:
        for node in sorted(graph.nodes()):
            if node in independent_set:
                file.write("1\n")
            else:
                file.write("0\n")

def process_graphs_in_folder(folder_path, output_folder, output_file, num_workers):
    mis_sizes = []
    graph_files = [os.path.join(folder_path, filename) for filename in os.listdir(folder_path) if filename.endswith(".gpickle")]
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit tasks to the executor
        future_to_graph = {executor.submit(process_graph_file, graph_file, output_folder): graph_file for graph_file in graph_files}
        
        for future in as_completed(future_to_graph):
            try:
                mis_size = future.result()
                mis_sizes.append(mis_size)
            except Exception as e:
                print(f"Error processing file {future_to_graph[future]}: {e}")
    
    # Write the MIS sizes to the output file
    write_mis_sizes_to_file(mis_sizes, output_file)
    
    # Calculate the average MIS size
    if mis_sizes:
        average_mis_size = sum(mis_sizes) / len(mis_sizes)
    else:
        average_mis_size = 0
    
    return mis_sizes, average_mis_size

def write_mis_sizes_to_file(mis_sizes, output_file):
    with open(output_file, 'w') as file:
        file.write("MIS Sizes for each graph:\n")
        for i, size in enumerate(mis_sizes):
            file.write(f"Graph {i+1}: {size}\n")
        average_mis_size = sum(mis_sizes) / len(mis_sizes) if mis_sizes else 0
        file.write(f"\nAverage MIS Size: {average_mis_size}\n")

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Compute MIS for graphs in a folder and report results.")
    parser.add_argument("--folder_path", type=str, required=True, help="Path to the folder containing .gpickle files")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the output folder where result files will be saved")
    parser.add_argument("--output_file", type=str, required=True, help="Path to the output file where MIS sizes will be saved")
    parser.add_argument("--workers", type=int, default=None, help="Number of CPU cores to use (default: use all available cores)")
    
    args = parser.parse_args()
    
    # Ensure output folder exists
    os.makedirs(args.output_folder, exist_ok=True)
    
    # Process the graphs and calculate MIS sizes using parallel computation
    mis_sizes, average_mis_size = process_graphs_in_folder(args.folder_path, args.output_folder, args.output_file, args.workers)
    
    print(f"Processing complete. Results are saved in the output folder: {args.output_folder}")
    print(f"MIS sizes and average MIS size have been written to {args.output_file}")
    print(f"Average MIS Size: {average_mis_size}")

if __name__ == "__main__":
    main()

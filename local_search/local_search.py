import networkx as nx
import random
import argparse

def read_graph_from_gpickle(file_path):
    """
    Reads a graph from a gpickle file.
    """
    return nx.read_gpickle(file_path)

def build_adjacency_list(graph):
    """
    Converts the graph into an adjacency list (dictionary of sets).
    This allows for O(1) neighbor lookups and edge checks.
    """
    adj_list = {node: set(graph.neighbors(node)) for node in graph.nodes()}
    return adj_list

def find_2_improvement(graph_adj_list, independent_set):
    """
    Attempts to find a 2-improvement by removing a vertex from the independent set and
    adding two of its neighbors (if they satisfy the independence conditions).
    Randomizes the order of `v1` and `v2` to improve search diversity.
    Tracks ineligible nodes globally for the entire independent set.
    """
    ineligible_nodes = set()  # Global set to track ineligible nodes for all vertices

    # Iterate over each vertex in the independent set
    for vertex in independent_set:
        
        # Get neighbors of the current vertex
        neighbors = list(graph_adj_list[vertex])
        
        # Focus only on neighbors that are outside the independent set and not ineligible
        outside_neighbors = [n for n in neighbors if n not in independent_set and n not in ineligible_nodes]
        
        # Shuffle once for diversity
        random.shuffle(outside_neighbors)
        
        # Check pairs of these outside neighbors
        i = 0
        while i < len(outside_neighbors):  # Iterate using while to allow removal during iteration
            v1 = outside_neighbors[i]
            
            remaining_set = independent_set - {vertex}
            
            # Check if `v1` has edges to any vertex in `remaining_set`
            if any(u in graph_adj_list[v1] for u in remaining_set):
                # Mark v1 as ineligible globally and remove it from outside_neighbors
                ineligible_nodes.add(v1)
                outside_neighbors.pop(i)
                continue  # Skip to the next iteration with the same index
            
            # Now check v2 candidates (no need to reshuffle, reuse shuffled list)
            j = i + 1
            while j < len(outside_neighbors):  # Nested loop over v2 candidates
                v2 = outside_neighbors[j]
                
                # We do not mark `v2` as ineligible just because it's adjacent to `v1`
                if v1 == v2 or v2 in graph_adj_list[v1]:
                    j += 1
                    continue  # Skip to the next v2 candidate
                
                # Check if `v2` has no edges to any vertex in the remaining independent set
                if any(u in graph_adj_list[v2] for u in remaining_set):
                    # Mark v2 as ineligible globally and remove it from outside_neighbors
                    ineligible_nodes.add(v2)
                    outside_neighbors.pop(j)
                    continue  # Remove v2 and check the next candidate
                
                # If both v1 and v2 can be added, return the new improved independent set
                new_set = remaining_set | {v1, v2}
                return new_set
            
            i += 1  # Move to the next v1 candidate if v1 is valid
    
    # No 2-improvement found, return the original independent set
    return independent_set

def local_search_arw(graph, initial_set, max_iterations=100):
    """
    Local search algorithm using 2-improvement. Uses adjacency lists for faster neighbor lookups.
    """
    # Build adjacency list for efficient edge and neighbor lookups
    graph_adj_list = build_adjacency_list(graph)
    
    current_set = initial_set
    for _ in range(max_iterations):
        new_set = find_2_improvement(graph_adj_list, current_set)
        if new_set == current_set:
            # No improvement was found
            break
        current_set = new_set
    return current_set

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Process independent set in a graph.')
    
    parser.add_argument('--graph_file', type=str, required=True, help='Path to the gpickle file of the graph')
    parser.add_argument('--result_file', type=str, required=True, help='Path to the .result file containing the initial independent set')
    parser.add_argument('--improved_output', type=str, required=True, help='Path to output the improved independent set')
    parser.add_argument('--max_iterations', type=int, default=100, help='Maximum number of iterations for local search (default: 100)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Load the graph
    graph = read_graph_from_gpickle(args.graph_file)
    
    # Read the independent set from the .result file
    with open(args.result_file, 'r') as f:
        initial_set = {i for i, line in enumerate(f) if int(line.strip()) == 1}
    
    # Print the size of the initial independent set
    print(f"Initial independent set size: {len(initial_set)}")
    
    # Apply local search to improve the independent set using 2-improvement
    improved_set = local_search_arw(graph, initial_set, max_iterations=args.max_iterations)
    
    # Print the size of the improved independent set
    print(f"Improved independent set size: {len(improved_set)}")
    
    # Write the improved independent set to a file
    with open(args.improved_output, 'w') as f:
        for node in sorted(improved_set):
            f.write(f"{node}\n")
    print(f"Improved independent set written to {args.improved_output}")

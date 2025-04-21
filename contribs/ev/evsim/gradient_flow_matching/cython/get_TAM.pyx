from libcpp.vector cimport vector
from libcpp.queue cimport queue
import numpy as np
cimport numpy as np
cimport cython
from tqdm import tqdm
import psutil

cdef dict path_cache = {}

def is_enough_memory(double threshold_gb=10.0):
    mem = psutil.virtual_memory()
    avail_gb = mem.available / 1e9
    return avail_gb >= threshold_gb

@cython.boundscheck(False)
@cython.wraparound(False)
cdef vector[vector[int]] build_adjacency_list(np.ndarray[np.int32_t, ndim=2] edge_index, int n_nodes):
    cdef:
        int i, u, v
        int n_edges = edge_index.shape[0]
        vector[vector[int]] adj = vector[vector[int]](n_nodes)
    for i in range(n_edges):
        u = edge_index[i, 0]
        v = edge_index[i, 1]
        adj[u].push_back(v)
    return adj

@cython.boundscheck(False)
@cython.wraparound(False)
cdef vector[int] bfs(int source, int target, int n_nodes,
                     np.ndarray[np.int32_t, ndim=2] edge_index,
                     vector[vector[int]]& adj,
                     bint use_memoization,
                     double gb_threshold):

    cdef:
        int i, u, v
        vector[int] visited = vector[int](n_nodes, 0)
        vector[int] prev = vector[int](n_nodes, -1)
        queue[int] q
        vector[int] edge_path, reversed_path
        int n_edges = edge_index.shape[0]
        tuple cache_key = (source, target)

    if use_memoization and cache_key in path_cache:
        return path_cache[cache_key]

    visited[source] = 1
    q.push(source)

    while not q.empty():
        u = q.front()
        q.pop()
        if u == target:
            break
        for i in range(adj[u].size()):
            v = adj[u][i]
            if not visited[v]:
                visited[v] = 1
                prev[v] = u
                q.push(v)

    v = target
    while prev[v] != -1:
        u = prev[v]
        for i in range(n_edges):
            if edge_index[i, 0] == u and edge_index[i, 1] == v:
                edge_path.push_back(i)
                break
        v = u

    for i in range(edge_path.size() - 1, -1, -1):
        reversed_path.push_back(edge_path[i])

    if use_memoization and is_enough_memory(gb_threshold):
        path_cache[cache_key] = reversed_path

    return reversed_path

@cython.boundscheck(False)
@cython.wraparound(False)
def get_TAM(dict cluster_lists,
            np.ndarray[np.int32_t, ndim=2] edge_index,
            int n_nodes,
            int n_edges,
            int n_clusters,
            int n_samples,
            bint use_memoization,
            double gb_threshold):

    cdef:
        int cluster1, cluster2
        int origin, dest, i, idx
        object origins, dests
        vector[int] path
        np.ndarray[np.float64_t, ndim=3] TAM = np.zeros((n_edges, n_clusters, n_clusters), dtype=np.float64)
        vector[vector[int]] adj = build_adjacency_list(edge_index, n_nodes)

    pbar = tqdm(total=(n_clusters * (n_clusters - 1)), desc="Creating TAM")
    for cluster1 in range(n_clusters):
        for cluster2 in range(n_clusters):
            if cluster1 == cluster2:
                continue

            pbar.update(1)
            origins = cluster_lists[cluster1]
            dests = cluster_lists[cluster2]

            for i in range(n_samples):
                origin = origins[np.random.randint(0, len(origins))]
                dest = dests[np.random.randint(0, len(dests))]
                path = bfs(origin, dest, n_nodes, edge_index, adj, use_memoization, gb_threshold)
                for idx in path:
                    TAM[idx, cluster1, cluster2] += 1

    TAM = TAM / n_samples
    return TAM


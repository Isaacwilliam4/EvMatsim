from libc.stdlib cimport rand, srand
from libcpp.vector cimport vector
from libcpp.queue cimport queue
from cython.parallel import prange
import numpy as np
cimport numpy as np
cimport cython

@cython.boundscheck(False)
@cython.wraparound(False)
cdef vector[int] bfs(int source, int target, int n_nodes,
                     np.ndarray[np.int32_t, ndim=2] edge_index):
    cdef:
        int i, u, v
        vector[vector[int]] adj = vector[vector[int]](n_nodes)
        vector[int] visited = vector[int](n_nodes, 0)
        vector[int] prev = vector[int](n_nodes, -1)
        queue[int] q
        vector[int] edge_path, reversed_path

    for i in range(edge_index.shape[0]):
        u = edge_index[i, 0]
        v = edge_index[i, 1]
        adj[u].push_back(v)

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
        for i in range(edge_index.shape[0]):
            if edge_index[i, 0] == u and edge_index[i, 1] == v:
                edge_path.push_back(i)
                break
        v = u

    for i in range(edge_path.size() - 1, -1, -1):
        reversed_path.push_back(edge_path[i])

    return reversed_path


@cython.boundscheck(False)
@cython.wraparound(False)
def sample_od_pairs(dict cluster_lists,
                    np.ndarray[np.int32_t, ndim=2] edge_index,
                    int n_nodes,
                    int n_edges,
                    int n_clusters,
                    int n_samples):

    cdef:
        int job_idx, total_jobs = 24 * n_clusters * n_clusters
        int hour, cluster1, cluster2
        int origin, dest, i, flat_idx
        object origins, dests
        vector[int] path
        np.ndarray[np.float64_t, ndim=4] TAM = np.zeros((24, n_edges, n_clusters, n_clusters), dtype=np.float64)

    for job_idx in prange(total_jobs, nogil=True):
        hour = job_idx // (n_clusters * n_clusters)
        flat_idx = job_idx % (n_clusters * n_clusters)
        cluster1 = flat_idx // n_clusters
        cluster2 = flat_idx % n_clusters

        if cluster1 == cluster2:
            continue

        with gil:
            origins = cluster_lists[cluster1]
            dests = cluster_lists[cluster2]

        for i in range(n_samples):
            with gil:
                origin = origins[np.random.randint(0, len(origins))]
                dest = dests[np.random.randint(0, len(dests))]

                path = bfs(origin, dest, n_nodes, edge_index)

                for idx in path:
                    TAM[hour, idx, cluster1, cluster2] += 1

    TAM_sum = np.sum(TAM, axis=1, keepdims=True)
    TAM_sum[TAM_sum == 0] = 1
    TAM = TAM / TAM_sum

    return TAM

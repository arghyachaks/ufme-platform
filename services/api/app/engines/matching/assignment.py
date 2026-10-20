"""Maximum-weight bipartite assignment (global 1:1). SciPy when installed; exact pure-Python Hungarian otherwise."""

from collections.abc import Sequence

try:  # pragma: no cover
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    def max_weight_assignment(weights: Sequence[Sequence[float]]) -> list[tuple[int, int]]:
        if not weights or not weights[0]:
            return []
        matrix = np.asarray(weights, dtype=float)
        rows, cols = linear_sum_assignment(matrix, maximize=True)
        return [(int(r), int(c)) for r, c in zip(rows, cols, strict=True) if matrix[r, c] > 0]

except ImportError:  # pragma: no cover

    def max_weight_assignment(weights: Sequence[Sequence[float]]) -> list[tuple[int, int]]:
        """Kuhn-Munkres on a padded square cost matrix (cost = max - weight). O(n^3)."""
        if not weights or not weights[0]:
            return []
        n_rows, n_cols = len(weights), len(weights[0])
        n = max(n_rows, n_cols)
        top = max(max(r) for r in weights)
        cost = [
            [(top - weights[i][j]) if i < n_rows and j < n_cols else top for j in range(n)] for i in range(n)
        ]
        inf = float("inf")
        u, v, p, way = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1), [0] * (n + 1)
        for i in range(1, n + 1):
            p[0], j0 = i, 0
            minv, used = [inf] * (n + 1), [False] * (n + 1)
            while True:
                used[j0] = True
                i0, delta, j1 = p[j0], inf, 0
                for j in range(1, n + 1):
                    if not used[j]:
                        cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                        if cur < minv[j]:
                            minv[j], way[j] = cur, j0
                        if minv[j] < delta:
                            delta, j1 = minv[j], j
                for j in range(n + 1):
                    if used[j]:
                        u[p[j]] += delta
                        v[j] -= delta
                    else:
                        minv[j] -= delta
                j0 = j1
                if p[j0] == 0:
                    break
            while True:
                j1 = way[j0]
                p[j0] = p[j1]
                j0 = j1
                if j0 == 0:
                    break
        out = []
        for j in range(1, n + 1):
            i = p[j]
            if i and i <= n_rows and j <= n_cols and weights[i - 1][j - 1] > 0:
                out.append((i - 1, j - 1))
        return sorted(out)

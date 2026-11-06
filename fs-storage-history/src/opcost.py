"""Least-squares estimate of new_stored per operation kind (diagnostic).

Each Commit applies five mixed operations, so per-operation cost is not
measured directly. This fits new_stored ≈ Σ_k c_k · n_k (no intercept;
the five counts always sum to 5) over every Commit of the given rows, using
the `applied` counts the Workspace reported and the Commit's `new_stored`.
Commits whose content another Branch already stored (H03) are excluded.
"""

KINDS = ("edit", "new", "delete", "rename", "append")


def solve(matrix, vector):
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        if abs(a[col][col]) < 1e-12:
            return None
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return [a[i][n] / a[i][i] for i in range(n)]


def samples(row, field="new_stored"):
    out = []
    for store in row["stores"]:
        for project in store["projects"]:
            for branch in project["branches"]:
                for commit in branch["commit_results"]:
                    counts = commit.get("applied") or {}
                    out.append(([counts.get(k, 0) for k in KINDS], commit[field]))
    return out


def fit(points):
    """Return {kind: bytes per operation} and the number of Commits used."""
    k = len(KINDS)
    xtx = [[sum(x[i] * x[j] for x, _ in points) for j in range(k)] for i in range(k)]
    xty = [sum(x[i] * y for x, y in points) for i in range(k)]
    coef = solve(xtx, xty)
    if coef is None:
        return None, len(points)
    return dict(zip(KINDS, coef)), len(points)

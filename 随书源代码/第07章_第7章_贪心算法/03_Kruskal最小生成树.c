#include <stdio.h>
#include <stdlib.h>

/* 边结构体 */
typedef struct {
    int src, dest, weight;
} Edge;

/* 并查集 */
typedef struct {
    int *parent, *rank;
    int n;
} UnionFind;

/* 创建并查集 */
UnionFind *create_uf(int n) {
    UnionFind *uf = (UnionFind *)malloc(sizeof(UnionFind));
    if (!uf) return NULL;
    uf->n = n;
    uf->parent = (int *)malloc(n * sizeof(int));
    uf->rank = (int *)malloc(n * sizeof(int));
    if (!uf->parent || !uf->rank) {
        free(uf->parent);
        free(uf->rank);
        free(uf);
        return NULL;
    }
    for (int i = 0; i < n; i++) {
        uf->parent[i] = i;
        uf->rank[i] = 0;
    }
    return uf;
}

void free_uf(UnionFind *uf) {
    if (!uf) return;
    free(uf->parent);
    free(uf->rank);
    free(uf);
}

/* 查找（带路径压缩） */
int find(UnionFind *uf, int x) {
    if (uf->parent[x] != x)
        uf->parent[x] = find(uf, uf->parent[x]);
    return uf->parent[x];
}

/* 合并（按秩合并）：
   与上方 find 中的路径压缩配套使用，
   使并查集操作的均摊复杂度非常接近常数级。 */
void union_sets(UnionFind *uf, int x, int y) {
    int rx = find(uf, x);
    int ry = find(uf, y);
    if (rx == ry) return;
    if (uf->rank[rx] < uf->rank[ry])
        uf->parent[rx] = ry;
    else if (uf->rank[rx] > uf->rank[ry])
        uf->parent[ry] = rx;
    else {
        uf->parent[ry] = rx;
        uf->rank[rx]++;
    }
}

/* 边比较函数 */
int compare_edge(const void *a, const void *b) {
    const Edge *x = (const Edge *)a;
    const Edge *y = (const Edge *)b;
    return (x->weight > y->weight) - (x->weight < y->weight);
}

/* Kruskal 算法 */
int kruskal(Edge edges[], int V, int E) {
    qsort(edges, E, sizeof(Edge), compare_edge);

    UnionFind *uf = create_uf(V);
    if (!uf) return 0;
    int edgeCount = 0;
    int totalWeight = 0;

    printf("最小生成树的边：\n");

    for (int i = 0; i < E && edgeCount < V - 1; i++) {
        int u = edges[i].src;
        int v = edges[i].dest;

        /* 不在同一连通分量，可以加入 */
        if (find(uf, u) != find(uf, v)) {
            printf("  村庄 %d - 村庄 %d，造价：%d\n", u, v, edges[i].weight);
            totalWeight += edges[i].weight;
            union_sets(uf, u, v);
            edgeCount++;
        }
    }

    printf("总造价：%d\n", totalWeight);
    free_uf(uf);
    return edgeCount == V - 1;
}

int main(void) {
    Edge edges[] = {
        {0, 1, 1}, {2, 3, 2}, {1, 2, 3},
        {0, 2, 4}, {1, 3, 5}, {0, 3, 6}
    };
    int V = 4;  /* 4 个村庄 */
    int E = sizeof(edges) / sizeof(edges[0]);

    if (!kruskal(edges, V, E)) {
        printf("图不连通，或内存不足，无法形成生成树\n");
        return 1;
    }
    return 0;
}

#include <stdio.h>
#include <string.h>
#include <limits.h>

#define MAXN 205    /* 最大节点数 */
#define INF 0x3f3f3f3f3f3f3f3fLL  /* 一个足够大的 long long 数 */

long long capacity[MAXN][MAXN];  /* 容量矩阵 */
long long flow[MAXN][MAXN];      /* 流量矩阵 */
int prev_node[MAXN];       /* BFS 中记录增广路径上的前驱节点 */
int visited[MAXN];         /* BFS 中的访问标记 */
int queue[MAXN];           /* BFS 用的队列 */

/* BFS 找增广路径 */
int bfs(int s, int t, int n) {
    int front = 0, rear = 0;
    int u, v;

    /* 初始化 */
    memset(visited, 0, sizeof(visited));
    memset(prev_node, -1, sizeof(prev_node));

    /* 将源点加入队列 */
    queue[rear++] = s;
    visited[s] = 1;

    while (front < rear) {
        u = queue[front++];

        /* 遍历 u 的所有邻居 */
        for (v = 0; v < n; v++) {
            /* 如果 v 未被访问，且残余容量大于 0 */
            if (!visited[v] && capacity[u][v] - flow[u][v] > 0) {
                visited[v] = 1;
                prev_node[v] = u;
                queue[rear++] = v;

                /* 如果到达汇点，找到了增广路径 */
                if (v == t) {
                    return 1;
                }
            }
        }
    }

    /* 没找到增广路径 */
    return 0;
}

/* Edmonds-Karp 算法求最大流 */
long long edmonds_karp(int s, int t, int n) {
    long long max_flow = 0;
    int u, v;
    long long path_flow;

    /* 只要还能找到增广路径，就继续 */
    while (bfs(s, t, n)) {
        /* 找到增广路径上的最小剩余容量（瓶颈） */
        path_flow = INF;
        for (v = t; v != s; v = prev_node[v]) {
            u = prev_node[v];
            if (capacity[u][v] - flow[u][v] < path_flow) {
                path_flow = capacity[u][v] - flow[u][v];
            }
        }

        /* 更新路径上每条边的流量 */
        for (v = t; v != s; v = prev_node[v]) {
            u = prev_node[v];
            flow[u][v] += path_flow;  /* 正向边加流量 */
            flow[v][u] -= path_flow;  /* 反向边减流量（允许退水） */
        }

        max_flow += path_flow;
    }

    return max_flow;
}

/*
 * 在最大流已经求完之后，寻找最小割。
 *
 * 思路：
 * 1. 在最终残余图中，从源点 s 出发做 BFS；
 * 2. 能到达的点属于集合 S；
 * 3. 不能到达的点属于集合 T；
 * 4. 回到原图中，所有从 S 指向 T 的边，就是最小割边。
 */
void find_min_cut(int s, int n) {
    int front = 0, rear = 0;
    int u, v;
    long long cut_capacity = 0;

    memset(visited, 0, sizeof(visited));

    /* 从源点 s 出发，在最终残余图中做 BFS */
    queue[rear++] = s;
    visited[s] = 1;

    while (front < rear) {
        u = queue[front++];

        for (v = 0; v < n; v++) {
            /*
             * 这里走的是残余图：
             * capacity[u][v] - flow[u][v] > 0
             * 表示 u 到 v 还有剩余容量，可以继续走。
             */
            if (!visited[v] && capacity[u][v] - flow[u][v] > 0) {
                visited[v] = 1;
                queue[rear++] = v;
            }
        }
    }

    printf("集合 S 中的节点: ");
    for (u = 0; u < n; u++) {
        if (visited[u]) {
            printf("%d ", u);
        }
    }
    printf("\n");

    printf("集合 T 中的节点: ");
    for (u = 0; u < n; u++) {
        if (!visited[u]) {
            printf("%d ", u);
        }
    }
    printf("\n");

    printf("最小割边:\n");

    /*
     * 回到原图中找割边：
     * u 在 S 中，v 在 T 中，并且原图里存在边 u→v。
     */
    for (u = 0; u < n; u++) {
        if (visited[u]) {  /* u 属于 S */
            for (v = 0; v < n; v++) {
                if (!visited[v] && capacity[u][v] > 0) {  /* v 属于 T */
                    printf("%d -> %d, 容量 = %lld\n", u, v, capacity[u][v]);
                    cut_capacity += capacity[u][v];
                }
            }
        }
    }

    printf("最小割容量: %lld\n", cut_capacity);
}

int main(void) {
    int n, m;
    int u, v;
    long long c;

    /* 初始化 */
    memset(capacity, 0, sizeof(capacity));
    memset(flow, 0, sizeof(flow));

    printf("请输入节点数和边数: ");
    scanf("%d %d", &n, &m);

    printf("请输入每条边(起点 终点 容量):\n");
    for (int i = 0; i < m; i++) {
        scanf("%d %d %lld", &u, &v, &c);
        capacity[u][v] += c;  /* 教学代码把重边合并为一条总容量边 */
    }

    /* 本例采用 0 到 n - 1 编号，源点为 0，汇点为 n - 1。 */
    long long ans = edmonds_karp(0, n - 1, n);
    printf("最大流: %lld\n", ans);

    find_min_cut(0, n);

    return 0;
}

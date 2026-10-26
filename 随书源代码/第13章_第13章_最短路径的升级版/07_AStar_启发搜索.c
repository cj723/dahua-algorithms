#include <stdio.h>
#include <math.h>

#define MAX_V 100
#define INF 0x3f3f3f3f

/* 启发函数：用欧几里得距离。
 * x[], y[] 由调用方传入，返回值向下取整，降低高估风险。
 * 这种写法要求边权能反映几何距离，且不小于两点直线距离。 */
int heuristic(int node, int goal, int x[], int y[]) {
    double dx = (double)x[node] - x[goal];
    double dy = (double)y[node] - y[goal];
    return (int)sqrt(dx * dx + dy * dy);
}

/* A* 搜索（简化版，邻接矩阵）。
 * 为了演示完整结果，这里额外记录 parent 用于还原路径。 */
void a_star(int graph[][MAX_V], int V, int src, int dest,
           int x[], int y[]) {
    int g[MAX_V];       /* 起点到各点的实际距离 */
    int f[MAX_V];       /* f = g + h */
    int closed[MAX_V];  /* 已处理的顶点 */
    int parent[MAX_V];  /* 记录路径 */

    for (int i = 0; i < V; i++) {
        g[i] = INF;
        f[i] = INF;
        closed[i] = 0;
        parent[i] = -1;
    }
    g[src] = 0;
    f[src] = heuristic(src, dest, x, y);

    while (1) {
        /* 选 f 值最小的顶点 */
        int u = -1;
        int minF = INF;
        for (int i = 0; i < V; i++) {
            if (!closed[i] && f[i] < minF) {
                minF = f[i];
                u = i;
            }
        }

        if (u == -1 || u == dest) break;
        closed[u] = 1;

        for (int v = 0; v < V; v++) {
            if (!closed[v] && graph[u][v] != 0 && g[u] != INF) {
                int newG = g[u] + graph[u][v];
                if (newG < g[v]) {
                    g[v] = newG;
                    f[v] = newG + heuristic(v, dest, x, y);
                    parent[v] = u;
                }
            }
        }
    }

    /* 输出结果 */
    if (g[dest] == INF) {
        printf("从 %d 到 %d 不可达\n", src, dest);
    } else {
        printf("从 %d 到 %d 的最短距离：%d\n", src, dest, g[dest]);
        printf("路径：");
        int path[MAX_V], len = 0;
        for (int v = dest; v != -1; v = parent[v])
            path[len++] = v;
        for (int i = len - 1; i >= 0; i--)
            printf("%d ", path[i]);
        printf("\n");
    }
}

/* 测试：A* 算法 */
int main(void) {
    int V = 5;
    int graph[MAX_V][MAX_V] = {0};
    int x[MAX_V] = {0, 2, 4, 4, 6};
    int y[MAX_V] = {0, 0, 2, -2, 0};

    /* 构建一个带坐标的小图 */
    graph[0][1] = 2; graph[0][2] = 4;
    graph[1][2] = 1; graph[1][3] = 7;
    graph[2][3] = 3; graph[2][4] = 5;
    graph[3][4] = 2;

    printf("A* 搜索演示（5 个顶点，带坐标的启发式搜索）\n");
    printf("顶点坐标：0(0,0) 1(2,0) 2(4,2) 3(4,-2) 4(6,0)\n\n");

    a_star(graph, V, 0, 4, x, y);

    return 0;
}

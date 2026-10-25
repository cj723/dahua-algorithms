#include <stdio.h>
#include <limits.h>
#include <string.h>

/*
 * Dijkstra 算法简化版
 *
 * 类比：你站在上海某个路口，想去东方明珠
 * 每到一个路口，你就问“从出发到这里走了多久？”
 * 然后选最快的那条路继续走
 */

#define V 6          /* 路口数量 */
#define INF 99999    /* 无穷大（不通） */

int min_distance(int dist[], int visited[]) {
    int min = INF, min_index = -1;
    int v;
    for (v = 0; v < V; v++) {
        if (!visited[v] && dist[v] < min) {
            min = dist[v];
            min_index = v;
        }
    }
    return min_index;
}

void dijkstra(int graph[V][V], int src) {
    int dist[V];     /* 从起点到每个路口的最短时间 */
    int visited[V];  /* 是否已经“走过” */
    int count, u, v;

    /* 初始化：所有路口都是“无穷远” */
    for (int i = 0; i < V; i++) {
        dist[i] = INF;
        visited[i] = 0;
    }
    dist[src] = 0;  /* 起点到自己的距离是 0 */

    for (count = 0; count < V - 1; count++) {
        /* 找当前最近的未访问路口 */
        u = min_distance(dist, visited);
        if (u == -1) break;
        visited[u] = 1;

        /* 更新 u 的所有邻居的距离 */
        for (v = 0; v < V; v++) {
            if (!visited[v] && graph[u][v] &&
                dist[u] + graph[u][v] < dist[v]) {
                dist[v] = dist[u] + graph[u][v];
            }
        }
    }

    printf("从路口 %d 出发的最短时间：\n", src);
    for (int i = 0; i < V; i++) {
        printf("  到路口 %d：%d 分钟\n", i, dist[i]);
    }
}

int main(void) {
    /* 邻接矩阵：graph[i][j] 表示从 i 到 j 的通行时间（分钟） */
    /* 本例假设所有通行时间都是正整数，0 表示不通；如果允许 0 权边，应改用 INF 或邻接表表示无边 */
    int graph[V][V] = {
    /*    0    1    2    3    4    5  */
        {  0,   4,   2,   0,   0,   0 },  /* 路口 0 */
        {  4,   0,   1,   5,   0,   0 },  /* 路口 1 */
        {  2,   1,   0,   8,  10,   0 },  /* 路口 2 */
        {  0,   5,   8,   0,   2,   6 },  /* 路口 3 */
        {  0,   0,  10,   2,   0,   3 },  /* 路口 4 */
        {  0,   0,   0,   6,   3,   0 }   /* 路口 5 */
    };

    dijkstra(graph, 0);  /* 从路口 0 出发 */

    return 0;
}

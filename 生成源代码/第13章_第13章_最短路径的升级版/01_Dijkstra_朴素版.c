#include <stdio.h>
#include <limits.h>

#define MAX_V 1000
#define INF 0x3f3f3f3f  /* 约 10 亿，两个 INF 相加也不会溢出 int */

/* 简化版：用邻接矩阵，朴素 O(V^2) 实现
 * 约定：graph[u][v] == 0 表示无边，因此本教学版不支持 0 权边。 */
void dijkstra(int graph[][MAX_V], int V, int src) {
    int dist[MAX_V];    /* 起点到各顶点的当前最短距离 */
    int visited[MAX_V]; /* 是否已经确定最短距离 */
    
    for (int i = 0; i < V; i++) {
        dist[i] = INF;
        visited[i] = 0;
    }
    dist[src] = 0;
    
    for (int count = 0; count < V; count++) {
        int u = -1;
        int minDist = INF;

        /* 找出当前距离最小的未确定顶点 */
        for (int v = 0; v < V; v++) {
            if (!visited[v] && dist[v] < minDist) {
                minDist = dist[v];
                u = v;
            }
        }
        
        if (u == -1) break; /* 剩余顶点不可达 */
        visited[u] = 1;
        
        /* 用 u 去更新其他顶点 */
        for (int v = 0; v < V; v++) {
            /* 若允许 0 权边，应改用 hasEdge[u][v] 或邻接表判断边是否存在 */
            if (!visited[v] && graph[u][v] != 0) {
                int newDist = dist[u] + graph[u][v];
                if (newDist < dist[v]) {
                    dist[v] = newDist;
                }
            }
        }
    }
    
    printf("从顶点 %d 出发的最短距离：\n", src);
    for (int i = 0; i < V; i++) {
        if (dist[i] == INF)
            printf("到顶点 %d: 不可达\n", i);
        else
            printf("到顶点 %d: %d\n", i, dist[i]);
    }
}


/* 测试：Dijkstra 朴素版最短路径 */
int main(void) {
    int V = 5;
    int graph[MAX_V][MAX_V] = {0};

    /* 构建测试图（邻接矩阵，0 表示无边） */
    graph[0][1] = 10; graph[0][2] = 3;
    graph[1][2] = 1;  graph[1][3] = 2;
    graph[2][1] = 4;  graph[2][3] = 8; graph[2][4] = 2;
    graph[3][4] = 7;
    graph[4][3] = 9;

    printf("图结构（5 个顶点）：\n");
    printf("  0 --10--> 1,  0 --3--> 2\n");
    printf("  1 --1--> 2,   1 --2--> 3\n");
    printf("  2 --4--> 1,   2 --8--> 3,  2 --2--> 4\n");
    printf("  3 --7--> 4\n\n");

    dijkstra(graph, V, 0);

    return 0;
}

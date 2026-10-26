#include <stdio.h>

#define MAX_V 100
#define INF 0x3f3f3f3f

/* 边的结构体 */
typedef struct {
    int src, dest, weight;
} Edge;

void bellman_ford(Edge edges[], int V, int E, int src) {
    int dist[MAX_V];
    
    /* 初始化 */
    for (int i = 0; i < V; i++)
        dist[i] = INF;
    dist[src] = 0;
    
    /* 松弛 V - 1 轮 */
    for (int i = 0; i < V - 1; i++) {
        int updated = 0;
        for (int j = 0; j < E; j++) {
            int u = edges[j].src;
            int v = edges[j].dest;
            int w = edges[j].weight;
            if (dist[u] != INF && dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                updated = 1;
            }
        }
        if (!updated) break;  /* 这一轮没有任何更新，提前结束 */
    }
    
    /* 检测负权环：再松弛一轮，如果还有更新，说明有从源点可达的负权环 */
    for (int j = 0; j < E; j++) {
        int u = edges[j].src;
        int v = edges[j].dest;
        int w = edges[j].weight;
        if (dist[u] != INF && dist[u] + w < dist[v]) {
            printf("警告：存在从源点可达的负权环！\n");
            return;
        }
    }
    
    /* 输出结果 */
    for (int i = 0; i < V; i++) {
        if (dist[i] == INF)
            printf("到顶点 %d: 不可达\n", i);
        else
            printf("到顶点 %d: %d\n", i, dist[i]);
    }
}


/* 测试：Bellman-Ford（可处理负权边） */
int main(void) {
    Edge edges[] = {
        {0, 1, -1}, {0, 2, 4},
        {1, 2, 3},  {1, 3, 2}, {1, 4, 2},
        {3, 2, 5},  {3, 1, 1},
        {4, 3, -3}
    };
    int V = 5, E = 8;

    printf("Bellman-Ford 从顶点 0 出发：\n");
    printf("边的条数：%d（含负权边）\n\n", E);
    bellman_ford(edges, V, E, 0);

    return 0;
}

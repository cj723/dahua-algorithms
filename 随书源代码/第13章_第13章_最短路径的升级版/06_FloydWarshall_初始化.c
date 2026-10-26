#include <stdio.h>

#define MAX_V 10
#define INF 0x3f3f3f3f

/* Floyd 算法的距离矩阵初始化演示 */
int main(void) {
    int V = 5;
    int graph[MAX_V][MAX_V] = {0};
    int dist[MAX_V][MAX_V];

    /* 先构建邻接矩阵。教学简化：0 表示无边，因此不能表达 0 权边。 */
    graph[0][1] = 3; graph[0][2] = 8; graph[0][4] = -4;
    graph[1][3] = 1; graph[1][4] = 7;
    graph[2][1] = 4;
    graph[3][0] = 2; graph[3][2] = -5;
    graph[4][3] = 6;

    /* dist[i][j] 初始化（Floyd 算法的第一步） */
    for (int i = 0; i < V; i++) {
        for (int j = 0; j < V; j++) {
            if (i == j)
                dist[i][j] = 0;           /* 自己到自己距离为 0 */
            else if (graph[i][j] != 0)
                dist[i][j] = graph[i][j];  /* 有边就用边的权重 */
            else
                dist[i][j] = INF;          /* 无边则无穷大 */
        }
    }

    printf("Floyd 初始化后的距离矩阵：\n");
    printf("（0=自己，INF=不可直达）\n\n");
    for (int i = 0; i < V; i++) {
        for (int j = 0; j < V; j++) {
            if (dist[i][j] == INF)
                printf(" INF");
            else
                printf("%4d", dist[i][j]);
        }
        printf("\n");
    }

    return 0;
}

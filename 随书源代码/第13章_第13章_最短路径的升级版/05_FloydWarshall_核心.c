#include <stdio.h>

#define MAX_V 100
#define INF 0x3f3f3f3f

void floyd(int dist[][MAX_V], int V) {
    /* 三重循环：k 是中转站 */
    for (int k = 0; k < V; k++) {
        for (int i = 0; i < V; i++) {
            for (int j = 0; j < V; j++) {
                /* 防溢出：只有两边都可达时才尝试更新 */
                if (dist[i][k] != INF && dist[k][j] != INF &&
                    dist[i][k] + dist[k][j] < dist[i][j]) {
                    dist[i][j] = dist[i][k] + dist[k][j];
                }
            }
        }
    }
}


/* 测试：Floyd-Warshall 全源最短路径 */
int main(void) {
    int V = 4;
    int dist[MAX_V][MAX_V];

    /* 初始化距离矩阵 */
    for (int i = 0; i < V; i++)
        for (int j = 0; j < V; j++)
            dist[i][j] = (i == j) ? 0 : INF;

    /* 设置边的权重 */
    dist[0][1] = 5;  dist[0][3] = 10;
    dist[1][2] = 3;
    dist[2][3] = 1;

    printf("原始图（4 个顶点）：\n");
    printf("  0 --5--> 1,  0 --10--> 3\n");
    printf("  1 --3--> 2\n");
    printf("  2 --1--> 3\n\n");

    floyd(dist, V);

    printf("Floyd 全源最短路径：\n");
    for (int i = 0; i < V; i++) {
        for (int j = 0; j < V; j++) {
            if (dist[i][j] == INF)
                printf("  INF");
            else
                printf("%5d", dist[i][j]);
        }
        printf("\n");
    }

    return 0;
}

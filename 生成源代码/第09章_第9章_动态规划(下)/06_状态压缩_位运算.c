#include <stdio.h>
#include <limits.h>

#define N 4            /* 城市数量 */
#define INF 1000000

/* dist[a][b] 表示城市 a 到 b 的距离 */
int dist[N][N] = {
    {0, 10, 15, 20},
    {10, 0, 35, 25},
    {15, 35, 0, 30},
    {20, 25, 30, 0}
};

/* dp[mask][i]：已访问城市集合为 mask，当前在城市 i 的最短路径 */
/* mask 用二进制位表示，如 mask=0b1011 表示访问了城市 0、1、3 */
int dp[1 << N][N];

/* TSP：从城市 0 出发，访问所有城市恰好一次，回到 0 的最短路径 */
int tsp(void) {
    int all = (1 << N) - 1;  /* 全 1：所有城市都访问过 */

    /* 初始化 dp 为无穷大 */
    for (int mask = 0; mask < (1 << N); mask++)
        for (int i = 0; i < N; i++)
            dp[mask][i] = INF;

    /* 起点：只访问了城市 0，当前在城市 0，路径长为 0 */
    dp[1][0] = 0;

    /* 遍历所有状态 */
    for (int mask = 1; mask < (1 << N); mask++) {
        for (int i = 0; i < N; i++) {
            /* 如果城市 i 不在 mask 中，跳过 */
            if (!(mask & (1 << i))) continue;
            if (dp[mask][i] == INF) continue;

            /* 尝试从 i 走到下一个城市 j */
            for (int j = 0; j < N; j++) {
                if (mask & (1 << j)) continue;  /* j 已经访问过 */
                int nextMask = mask | (1 << j);
                int newDist = dp[mask][i] + dist[i][j];
                if (newDist < dp[nextMask][j])
                    dp[nextMask][j] = newDist;
            }
        }
    }

    /* 从最后访问的城市回到起点 0，取最小值 */
    int answer = INF;
    for (int i = 1; i < N; i++) {
        int total = dp[all][i] + dist[i][0];
        if (total < answer) answer = total;
    }
    return answer;
}

int main(void) {
    printf("城市距离矩阵：\n");
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++)
            printf("%3d ", dist[i][j]);
        printf("\n");
    }
    printf("\nTSP 最短路径（状态压缩DP）：%d\n", tsp());
    printf("状态总数：2^%d = %d，dp 大小：%d × %d\n",
           N, 1 << N, 1 << N, N);

    return 0;
}

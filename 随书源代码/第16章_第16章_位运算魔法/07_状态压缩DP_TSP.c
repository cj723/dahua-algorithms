#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 状态压缩 DP 示意（旅行商问题的简化版） */
/* 假设有 4 个城市，编号 0-3 */

#define MAXN 4           /* 城市数 */
#define INF 0x3f3f3f3f   /* 无穷大，两个 INF 相加也不会溢出 int */

int dist[MAXN][MAXN] = { /* 距离矩阵 */
    {0, 10, 15, 20},
    {10,  0, 35, 25},
    {15, 35,  0, 30},
    {20, 25, 30,  0}
};

int dp[1 << MAXN][MAXN];  /* dp[S][i]：已经访问集合 S，当前在城市 i 的最短距离 */
                          /* S 用 4 位二进制表示，最多 2^4 = 16 种状态 */

int tsp(void) {
    int S, full;
    
    /* 初始化所有状态为无穷大 */
    for (S = 0; S < (1 << MAXN); S++) {
        for (int i = 0; i < MAXN; i++) {
            dp[S][i] = INF;
        }
    }
    
    /* 起点：从城市 0 出发，状态为 0001 */
    dp[1][0] = 0;  /* 1 = 0001，表示只访问了城市 0 */
    
    /* 状态转移 */
    full = (1 << MAXN) - 1;  /* 1111，表示所有城市都访问了 */
    
    for (S = 1; S <= full; S++) {           /* 遍历所有状态 */
        for (int i = 0; i < MAXN; i++) {    /* 当前所在城市 */
            if (dp[S][i] == INF) continue;  /* 这个状态不可达 */
            if (!((S >> i) & 1)) continue;   /* 确认城市 i 在集合 S 中 */
            
            for (int j = 0; j < MAXN; j++) { /* 尝试去下一个城市 */
                if ((S >> j) & 1) continue;  /* 如果 j 已在集合中，跳过 */
                /* S | (1 << j)：把城市 j 加入访问集合 */
                int newS = S | (1 << j);
                if (dp[S][i] > INF - dist[i][j]) continue;  /* 防止 INF 加法溢出 */
                if (dp[S][i] + dist[i][j] < dp[newS][j]) {
                    dp[newS][j] = dp[S][i] + dist[i][j];
                }
            }
        }
    }
    
    /* 找到访问所有城市后的最短距离 */
    int ans = INF;
    for (int i = 0; i < MAXN; i++) {
        if (dp[full][i] == INF) continue;  /* 不可达状态不能参与加法 */
        if (dp[full][i] > INF - dist[i][0]) continue;
        if (dp[full][i] + dist[i][0] < ans) {
            ans = dp[full][i] + dist[i][0];  /* 加上回到起点的距离 */
        }
    }
    return ans;
}

int main(void) {
    printf("最短路径长度： %d\n", tsp());
    return 0;
}

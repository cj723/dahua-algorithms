#include <stdio.h>

#define N 4           /* 网页数量 */
#define DAMPING 0.85  /* 阻尼系数：模拟用户有 85% 的概率点链接，15% 随机跳转 */
#define ITERATIONS 20 /* 迭代次数 */

/*
 * PageRank 简化版
 *
 * 类比：每个网页是一个人，链接就是“投票”
 * 你链接到我，等于你投我一票
 * 但你的投票权 = 你的分数 / 你投出的票数
 */

int main(void) {
    /* 邻接矩阵：link[i][j] = 1 表示网页 i 链接到网页 j */
    int link[N][N] = {
        /*  A  B  C  D */
        { 0, 1, 1, 0 },  /* A → B, C */
        { 0, 0, 1, 0 },  /* B → C */
        { 1, 0, 0, 0 },  /* C → A */
        { 0, 0, 1, 0 }   /* D → C */
    };

    double rank[N];      /* 当前分数 */
    double newRank[N];   /* 新一轮的分数 */
    int iter;

    /* 初始化：每个网页都是1/N = 0.25 */
    for (int i = 0; i < N; i++) {
        rank[i] = 1.0 / N;
    }

    /* 计算每个网页的出链数 */
    int outDegree[N] = {0};
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (link[i][j]) outDegree[i]++;
        }
    }

    /* 迭代计算 */
    for (iter = 0; iter < ITERATIONS; iter++) {
        for (int j = 0; j < N; j++) {
            /* 网页 j 的新分数 = 阻尼 × 所有链向 j 的网页的贡献之和 + (1 - 阻尼) / N */
            newRank[j] = (1.0 - DAMPING) / N;
            for (int i = 0; i < N; i++) {
                if (link[i][j]) {
                    /* 网页 i 把自己的分数平均分给它链接的所有网页 */
                    newRank[j] += DAMPING * rank[i] / outDegree[i];
                }
            }
        }
        /* 更新 */
        for (int i = 0; i < N; i++) {
            rank[i] = newRank[i];
        }
    }

    printf("=== PageRank 结果 ===\n");
    for (int i = 0; i < N; i++) {
        printf("网页 %c: %.4f\n", 'A' + i, rank[i]);
    }

    return 0;
}

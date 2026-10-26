#include <stdio.h>
#include <math.h>

/*
 * 计算两个用户的相似度（皮尔逊相关系数简化版）
 * 就像比较两个人的“品味向量”
 *
 * 类比：你和小明各有一张打分卡
 * 你：  苹果 5  香蕉 3  橘子 4  西瓜 1
 * 小明：苹果 4  香蕉 4  橘子 5  西瓜 2
 * 越接近，说明口味越像
 */

#define NUM_ITEMS 4  /* 商品数量 */

/* 计算两个用户的相似度（皮尔逊相关系数简化版） */
double similarity(int userA[], int userB[], int n) {
    double sumA = 0, sumB = 0;
    double sumAB = 0, sumA2 = 0, sumB2 = 0;

    for (int i = 0; i < n; i++) {
        sumA  += userA[i];
        sumB  += userB[i];
        sumAB += userA[i] * userB[i];
        sumA2 += userA[i] * userA[i];
        sumB2 += userB[i] * userB[i];
    }

    /* 皮尔逊相关系数公式（"计算器公式"，适合小数据量教学演示） */
    double numerator = n * sumAB - sumA * sumB;
    double var_product = (n * sumA2 - sumA * sumA) * (n * sumB2 - sumB * sumB);
    if (var_product <= 0) return 0;  /* 防止浮点误差导致对负数开根号 */
    double denominator = sqrt(var_product);

    if (denominator == 0) return 0;
    return numerator / denominator;
}

int main(void) {
    /*           苹果  香蕉  橘子  西瓜 */
    int userA[] = {5,    3,    4,    1};  /* 你 */
    int userB[] = {4,    4,    5,    2};  /* 小明 */
    int userC[] = {1,    5,    2,    5};  /* 小红 */

    double simAB = similarity(userA, userB, NUM_ITEMS);
    double simAC = similarity(userA, userC, NUM_ITEMS);

    printf("你和小明的相似度：%.2f\n", simAB);
    printf("你和小红的相似度：%.2f\n", simAC);

    if (simAB > simAC) {
        printf("推荐：去看看小明喜欢什么！\n");
    } else {
        printf("推荐：去看看小红喜欢什么！\n");
    }

    return 0;
}

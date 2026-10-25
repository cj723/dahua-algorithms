/* 蓄水池抽样（Reservoir Sampling） */
/* 类比：不知道总共有多少人，但要公平抽样 */
/* 就像一边念名单一边抽奖，念完之前不知道有多少人 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 蓄水池抽样：从数据流中等概率抽取 k 个样本，返回实际抽到的样本数 */
/* 注意：为了让演示更清晰，这里用数组模拟数据流。 */
/* 真正的流式场景中，数据是逐个到达的，n 事先未知。 */
/* 实际使用时，应将下面的逻辑嵌入到数据到达的回调中。 */
int reservoir_sampling(int stream[], int n, int k, int result[]) {
    if (stream == NULL || result == NULL || n <= 0 || k <= 0) {
        return 0;  /* 没有可抽样数据 */
    }

    int sample_count = (k < n) ? k : n;

    /* 第 1 步：先把前 sample_count 个数据放入“蓄水池” */
    for (int i = 0; i < sample_count; i++) {
        result[i] = stream[i];  /* 直接放入 */
    }

    /* 第 2 步：对于第 k + 1 个及以后的数据，决定是否替换 */
    for (int i = k; i < n; i++) {
        /* 生成一个 [0, i] 之间的随机数 j */
        int j = rand() % (i + 1);

        /* 如果 j < k，就用当前数据替换蓄水池中的第 j 个 */
        if (j < k) {
            result[j] = stream[i];
        }
        /* 如果 j >= k，跳过当前数据 */
    }

    return sample_count;  /* 实际抽到的样本数，n < k 时会小于 k */
}

/* 测试：模拟从 100 个数据中抽取 5 个样本 */
int main(void) {
    int stream[100];    /* 数据流 */
    int result[5];      /* 抽样结果（蓄水池） */
    int n = 100;        /* 数据总数 */
    int k = 5;          /* 抽样数量 */

    srand((unsigned int)time(NULL));  /* 初始化随机种子 */

    /* 生成数据流：1 到 100 */
    for (int i = 0; i < n; i++) {
        stream[i] = i + 1;
    }

    /* 执行蓄水池抽样 */
    int sample_count = reservoir_sampling(stream, n, k, result);

    /* 输出抽样结果 */
    printf("从 1 到 %d 中抽取 %d 个样本：", n, sample_count);
    for (int i = 0; i < sample_count; i++) {
        printf("%d ", result[i]);
    }
    printf("\n");

    return 0;
}

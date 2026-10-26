#include <stdio.h>
#include <limits.h>

int max_profit(int *prices, int pricesSize) {
    if (pricesSize <= 1) return 0;

    int min_price = INT_MAX;  /* 到今天为止见过的最低价格 */
    int max_profit = 0;       /* 最大利润；如果一直亏，就不交易 */

    for (int i = 0; i < pricesSize; i++) {
        if (prices[i] < min_price) {
            min_price = prices[i];
        }

        int today_profit = prices[i] - min_price;
        if (today_profit > max_profit) {
            max_profit = today_profit;
        }
    }

    return max_profit;
}


// 测试：买卖股票最佳时机（一次交易）
int main(void) {
    int prices1[] = {7, 1, 5, 3, 6, 4};
    printf("价格[7,1,5,3,6,4] → 最大利润：%d（期望 5）\n",
           max_profit(prices1, 6));

    int prices2[] = {7, 6, 4, 3, 1};
    printf("价格[7,6,4,3,1] → 最大利润：%d（期望 0，一直跌不买）\n",
           max_profit(prices2, 5));

    printf("\n说明：一遍扫描，跟踪历史最低价，O(n) 时间，O(1) 空间\n");

    return 0;
}

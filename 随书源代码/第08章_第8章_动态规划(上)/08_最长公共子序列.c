#include <stdio.h>
#include <string.h>

#define MAX_LEN 1000

int max(int a, int b) {
    return a > b ? a : b;
}

int lcs_length(const char *X, const char *Y) {
    int m = (int)strlen(X);
    int n = (int)strlen(Y);

    if (m > MAX_LEN || n > MAX_LEN) {
        return -1;  /* 防止字符串过长导致 dp 数组越界 */
    }

    int dp[MAX_LEN + 1][MAX_LEN + 1];
    
    for (int i = 0; i <= m; i++) {
        dp[i][0] = 0;
    }
    for (int j = 0; j <= n; j++) {
        dp[0][j] = 0;
    }
    
    // 填表
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (X[i - 1] == Y[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }
    
    return dp[m][n];
}

int main(void) {
    char X[] = "ABCB";
    char Y[] = "BDCAB";
    printf("LCS 长度：%d\n", lcs_length(X, Y));
    return 0;
}

/* 位图(Bitmap)实现 */
/* 类比：出勤点名册——每个学生一个格子，来了打勾 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_NUM 1000000  /* 最大能存储的数 */

/* 位图结构 */
typedef struct {
    unsigned char *bits;  /* 位图数组，每个 char 有 8 个 bit */
    int size;             /* 数组大小(字节数) */
    int max;              /* 允许存储的最大数值 */
} Bitmap;

/* 创建位图 */
/* 参数 max：能存储的最大数值（允许下标为 0..max，共 max + 1 个 bit） */
Bitmap* bitmap_create(int max) {
    if (max < 0) {
        return NULL;
    }
    Bitmap *bm = (Bitmap *)malloc(sizeof(Bitmap));  /* 分配结构体内存 */
    if (bm == NULL) {
        printf("位图结构体内存分配失败\n");
        return NULL;
    }
    /* 需要的字节数 = 能存 max + 1 个 bit，向上取整 = (max >> 3) + 1 */
    /* 例如：max = 7 需要 1 字节（能存 0-7 共 8 个 bit） */
    /*       max = 8 需要 2 字节（存下标 0-8 共 9 个 bit，1 字节只有 8 位装不下） */
    bm->size = (max >> 3) + 1;
    bm->max = max;
    /* 分配位图数组，calloc 会自动初始化为 0 */
    bm->bits = (unsigned char *)calloc(bm->size, sizeof(unsigned char));
    if (bm->bits == NULL) {
        printf("位图数组内存分配失败\n");
        free(bm);
        return NULL;
    }
    return bm;
}

/* 设置第 n 个 bit 为 1（标记 n 存在） */
/* 参数 bm：位图指针；参数 n：要标记的数值 */
void bitmap_set(Bitmap *bm, int n) {
    if (bm == NULL || n < 0 || n > bm->max) return;
    int index = n >> 3;        /* n / 8，找到在第几个字节 */
    int offset = n & 7;        /* n % 8，找到在第几个 bit 位 */
    bm->bits[index] |= (1U << offset);  /* 把对应 bit 置为 1 */
    /* 1U << offset：生成一个只有第 offset 位是 1 的无符号数 */
    /* |=：或操作，把目标 bit 设为 1，不影响其他 bit */
}

/* 检查第 n 个 bit 是否为 1（检查 n 是否存在） */
int bitmap_get(Bitmap *bm, int n) {
    if (bm == NULL || n < 0 || n > bm->max) return 0;
    int index = n >> 3;        /* n / 8 */
    int offset = n & 7;        /* n % 8 */
    return (bm->bits[index] & (1U << offset)) != 0;
    /* & 操作：如果对应 bit 是 1，结果非 0；是 0，结果为 0 */
}

/* 清除第 n 个 bit（标记 n 不存在） */
void bitmap_clear(Bitmap *bm, int n) {
    if (bm == NULL || n < 0 || n > bm->max) return;
    int index = n >> 3;        /* n / 8 */
    int offset = n & 7;        /* n % 8 */
    bm->bits[index] &= ~(1U << offset);  /* 把对应 bit 清零 */
    /* ~ (1U << offset)：生成一个只有第 offset 位是 0 的无符号数 */
    /* &=：与操作，把目标 bit 清 0，不影响其他 bit */
}

/* 释放位图内存 */
void bitmap_destroy(Bitmap *bm) {
    if (bm == NULL) return;
    free(bm->bits);   /* 先释放bits数组 */
    free(bm);         /* 再释放结构体 */
}

/* 测试代码 */
int main(void) {
    Bitmap *bm = bitmap_create(MAX_NUM);  /* 创建一个能存 100 万个数的位图 */
    if (bm == NULL) {
        return 1;
    }
    
    /* 模拟出勤记录：学号 1、5、100、999999 来了 */
    bitmap_set(bm, 1);
    bitmap_set(bm, 5);
    bitmap_set(bm, 100);
    bitmap_set(bm, 999999);
    
    /* 检查出勤情况 */
    printf("学号 1 来了吗？%s\n", bitmap_get(bm, 1) ? "来了" : "没来");
    printf("学号 2 来了吗？%s\n", bitmap_get(bm, 2) ? "来了" : "没来");
    printf("学号 5 来了吗？%s\n", bitmap_get(bm, 5) ? "来了" : "没来");
    printf("学号 999999 来了吗？%s\n", bitmap_get(bm, 999999) ? "来了" : "没来");
    
    bitmap_destroy(bm);  /* 释放内存 */
    return 0;
}

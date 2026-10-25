/* 布隆过滤器(Bloom Filter)简化实现 */
/* 类比：安检门——"可能在，肯定不在" */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BLOOM_SIZE 1024   /* 位数组大小（bit 数） */
#define HASH_COUNT 3      /* 哈希函数个数 */
/* 误报率取决于 BLOOM_SIZE、HASH_COUNT 和插入元素数量，工程中要按需求估算参数 */

/* 布隆过滤器结构 */
typedef struct {
    unsigned char bits[(BLOOM_SIZE + 7) >> 3];  /* 位数组，用 char 数组模拟 */
} BloomFilter;

/* 简单的哈希函数 1（DJBX33A 变体） */
unsigned int hash1(const char *str) {
    unsigned int hash = 5381;   /* 初始种子 */
    while (*str) {
        hash = ((hash << 5) + hash) + (unsigned char)(*str++);  /* hash * 33 + c */
    }
    return hash % BLOOM_SIZE;   /* 映射到 bit 数组范围内 */
}

/* 简单的哈希函数 2（另一个种子） */
unsigned int hash2(const char *str) {
    unsigned int hash = 0;
    while (*str) {
        hash = (unsigned char)(*str++) + (hash << 6) + (hash << 16) - hash;
    }
    return hash % BLOOM_SIZE;
}

/* 简单的哈希函数 3（再换一个种子） */
unsigned int hash3(const char *str) {
    unsigned int hash = 0x12345678;  /* 不同的初始值 */
    while (*str) {
        hash ^= ((hash << 5) + (unsigned char)(*str++) + (hash >> 2));
    }
    return hash % BLOOM_SIZE;
}

/* 哈希函数数组，方便遍历 */
unsigned int (*hash_funcs[])(const char *) = {hash1, hash2, hash3};

/* 本例按字节处理字符串。UTF-8 中文会拆成多个字节参与哈希；
 * 工程中要先统一编码、大小写和归一化策略。 */

/* 设置 bit 数组中的某个 bit 为 1 */
static void set_bit(BloomFilter *bf, int pos) {
    bf->bits[pos >> 3] |= (1U << (pos & 7));
}

/* 检查 bit 数组中的某个 bit 是否为 1 */
static int get_bit(BloomFilter *bf, int pos) {
    return (bf->bits[pos >> 3] & (1U << (pos & 7))) != 0;
}

/* 初始化布隆过滤器 */
void bloom_init(BloomFilter *bf) {
    memset(bf->bits, 0, sizeof(bf->bits));  /* 全部清零 */
}

/* 插入元素 */
void bloom_insert(BloomFilter *bf, const char *str) {
    for (int i = 0; i < HASH_COUNT; i++) {
        unsigned int pos = hash_funcs[i](str);  /* 计算哈希位置 */
        set_bit(bf, pos);                        /* 把对应 bit 设为 1 */
    }
}

/* 查询元素是否存在 */
/* 返回 1 = 可能存在（有假阳性）；返回 0 = 肯定不存在 */
int bloom_contains(BloomFilter *bf, const char *str) {
    for (int i = 0; i < HASH_COUNT; i++) {
        unsigned int pos = hash_funcs[i](str);  /* 计算哈希位置 */
        if (!get_bit(bf, pos)) {                 /* 如果任一 bit 是 0 */
            return 0;                             /* 肯定不存在 */
        }
    }
    return 1;  /* 所有 bit 都是 1，可能存在 */
}

/* 测试代码 */
int main(void) {
    BloomFilter bf;
    bloom_init(&bf);  /* 初始化 */
    
    /* 插入一些元素 */
    bloom_insert(&bf, "苹果");
    bloom_insert(&bf, "香蕉");
    bloom_insert(&bf, "芒果");
    
    /* 查询 */
    printf("苹果：%s\n", bloom_contains(&bf, "苹果") ? "可能存在" : "肯定不存在");
    printf("香蕉：%s\n", bloom_contains(&bf, "香蕉") ? "可能存在" : "肯定不存在");
    printf("橙子：%s\n", bloom_contains(&bf, "橙子") ? "可能存在" : "肯定不存在");
    /* 橙子没有插入过，但可能因为假阳性说“可能存在” */
    
    return 0;
}

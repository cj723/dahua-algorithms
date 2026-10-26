#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#define ALPHABET_SIZE 26  /* 假设只处理小写字母 */

/* Trie 树节点 */
typedef struct TrieNode {
    struct TrieNode *children[ALPHABET_SIZE];
    bool is_end;  /* 是否是某个单词的结尾 */
} TrieNode;

/* 创建新节点 */
TrieNode *create_node(void) {
    TrieNode *node = (TrieNode *)malloc(sizeof(TrieNode));
    if (node == NULL) {
        printf("内存分配失败\n");
        exit(1);
    }
    node->is_end = false;
    for (int i = 0; i < ALPHABET_SIZE; i++) {
        node->children[i] = NULL;
    }
    return node;
}

/* 插入单词：本示例只处理 'a' 到 'z' */
void trie_insert(TrieNode *root, const char *word) {
    TrieNode *cur = root;
    for (int i = 0; word[i] != '\0'; i++) {
        int idx = word[i] - 'a';
        if (idx < 0 || idx >= ALPHABET_SIZE) {
            continue;  /* 简化处理：跳过非小写字母 */
        }
        if (cur->children[idx] == NULL) {
            cur->children[idx] = create_node();
        }
        cur = cur->children[idx];
    }
    cur->is_end = true;
}

/* 查找单词 */
bool trie_search(TrieNode *root, const char *word) {
    TrieNode *cur = root;
    for (int i = 0; word[i] != '\0'; i++) {
        int idx = word[i] - 'a';
        if (idx < 0 || idx >= ALPHABET_SIZE) {
            return false;
        }
        if (cur->children[idx] == NULL) {
            return false;  /* 路径断了，不存在 */
        }
        cur = cur->children[idx];
    }
    return cur->is_end;  /* 必须是完整单词的结尾 */
}

/* 检查是否存在以 prefix 为前缀的单词 */
bool trie_starts_with(TrieNode *root, const char *prefix) {
    TrieNode *cur = root;
    for (int i = 0; prefix[i] != '\0'; i++) {
        int idx = prefix[i] - 'a';
        if (idx < 0 || idx >= ALPHABET_SIZE) {
            return false;
        }
        if (cur->children[idx] == NULL) {
            return false;
        }
        cur = cur->children[idx];
    }
    return true;
}

/* 释放 Trie 树 */
void trie_free(TrieNode *root) {
    if (root == NULL) return;
    for (int i = 0; i < ALPHABET_SIZE; i++) {
        trie_free(root->children[i]);
    }
    free(root);
}

int main(void) {
    TrieNode *root = create_node();
    
    /* 插入一些单词 */
    trie_insert(root, "apple");
    trie_insert(root, "app");
    trie_insert(root, "ape");
    trie_insert(root, "bat");
    
    /* 查找 */
    printf("查找 'apple': %s\n", trie_search(root, "apple") ? "找到" : "未找到");
    printf("查找 'app': %s\n", trie_search(root, "app") ? "找到" : "未找到");
    printf("查找 'apex': %s\n", trie_search(root, "apex") ? "找到" : "未找到");
    printf("前缀 'ap': %s\n", trie_starts_with(root, "ap") ? "存在" : "不存在");
    
    trie_free(root);
    return 0;
}

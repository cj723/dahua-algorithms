#include <stdio.h>
#include <stdlib.h>

struct ListNode {
    int val;
    struct ListNode *next;
};

struct ListNode *detect_cycle(struct ListNode *head) {
    struct ListNode *slow = head;
    struct ListNode *fast = head;

    /* 1. 判断是否有环 */
    while (fast != NULL && fast->next != NULL) {
        slow = slow->next;          /* 龟走一步 */
        fast = fast->next->next;    /* 兔走两步 */

        /* 发现相遇，说明有环！ */
        if (slow == fast) {
            /* 2. 寻找环的入口 */
            fast = head;            /* 兔回到起点 */
            while (slow != fast) {
                slow = slow->next;  /* 两人现在同速 */
                fast = fast->next;
            }
            return slow;            /* 再次相遇的点，就是环入口 */
        }
    }
    return NULL;  /* 无环 */
}

/* 测试：环形链表检测 */
int main(void) {
    /* 构建链表 1 → 2 → 3 → 4 → 5，然后 5 指向 3 形成环 */
    struct ListNode nodes[5];
    for (int i = 0; i < 5; i++) {
        nodes[i].val = i + 1;
        nodes[i].next = (i < 4) ? &nodes[i+1] : &nodes[2];  // 5 → 3
    }

    struct ListNode *entry = detect_cycle(&nodes[0]);
    if (entry)
        printf("检测到环，入口为节点：%d\n", entry->val);
    else
        printf("无环\n");

    return 0;
}

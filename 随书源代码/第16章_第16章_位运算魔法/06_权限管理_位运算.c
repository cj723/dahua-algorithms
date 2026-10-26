#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 用位运算管理用户权限 */
/* 类比：钥匙扣——每把钥匙开一道门，权限就是钥匙的组合 */
/* 注意：这里为了演示把 READ 放在最低位，和 Unix rwx 中 r = 4, w = 2, x = 1 的编号方向不同 */

#define PERM_READ    0x01   /* 0001：读权限 */
#define PERM_WRITE   0x02   /* 0010：写权限 */
#define PERM_EXECUTE 0x04   /* 0100：执行权限 */
#define PERM_ADMIN   0x08   /* 1000：管理员权限 */

/* 检查是否有某项权限 */
/* 用 & 操作：如果对应 bit 是 1，说明有这个权限 */
int has_permission(int user_perm, int perm) {
    return (user_perm & perm) == perm;
}

/* 添加权限 */
/* 用 | 操作：把对应的 bit 设为 1 */
int add_permission(int user_perm, int perm) {
    return user_perm | perm;
}

/* 移除权限 */
/* 用 & ~ 操作：把对应的 bit 清 0 */
int remove_permission(int user_perm, int perm) {
    return user_perm & ~perm;
}

/* 测试 */
int main(void) {
    int user = PERM_READ;  /* 用户初始只有读权限 */
    printf("初始权限： %d\n", user);
    
    /* 检查权限 */
    printf("有读权限？%s\n", has_permission(user, PERM_READ) ? "是" : "否");
    printf("有写权限？%s\n", has_permission(user, PERM_WRITE) ? "是" : "否");
    
    /* 添加写权限 */
    user = add_permission(user, PERM_WRITE);
    printf("添加写权限后： %d\n", user);
    printf("现在有写权限？%s\n", has_permission(user, PERM_WRITE) ? "是" : "否");
    
    /* 移除读权限 */
    user = remove_permission(user, PERM_READ);
    printf("移除读权限后： %d\n", user);
    
    return 0;
}

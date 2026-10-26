# 大话算法

《大话算法》配套 C 语言源码与交互式算法演示网站。

- **在线演示**：https://cj723.github.io/dahua-algorithms/
- **随书源代码**：[随书源代码](随书源代码/)
- **样例网站**：[样例网站](样例网站/)

## 内容

- 122 份按章节整理的 C 语言示例，涵盖搜索、排序、贪心、动态规划、回溯、图、字符串、高级数据结构等。
- 23 个章节页面（第 0～22 章）及学习地图首页。
- 111 份预生成的执行轨迹 JSON；部分主题采用概念动画。
- 源码插桩、轨迹检查、章节页面生成脚本。

## 下载与运行源码

安装 Git 后克隆仓库，也可以点击 GitHub 的 **Code → Download ZIP** 下载。

```bash
git clone https://github.com/cj723/dahua-algorithms.git
cd dahua-algorithms
```

使用 GCC 或 Clang 编译需要学习的示例，例如：

```bash
cc -std=c11 "随书源代码/第01章_第1章_算法__你每天都在用/01_顺序查找.c" -o /tmp/dahua-example
/tmp/dahua-example
```

示例按教学主题组织，部分文件为代码片段，需要结合书中上下文阅读。涉及数学函数的示例在部分系统上需要在编译时添加 `-lm`。

## 本地预览网站

网站已包含可直接部署的静态页面，无需安装前端依赖。推荐在仓库根目录启动静态服务器：

```bash
python3 -m http.server 8000 --directory "样例网站"
```

浏览器访问 http://localhost:8000/ 。

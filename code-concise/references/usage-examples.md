# Code-Concise Skill 使用示例

本文档展示如何使用 code-concise 技能进行代码审查和优化。

## 示例 1：基本代码审查

### 用户请求
```
请审查这段代码：
```javascript
function processOrder(order) {
  if (order) {
    if (order.items) {
      if (order.items.length > 0) {
        let total = 0;
        for (let i = 0; i < order.items.length; i++) {
          const item = order.items[i];
          if (item.price) {
            total += item.price * item.quantity;
          }
        }
        if (total > 0.8 * 1000) {
          total = total * 0.9;
        }
        return total;
      }
    }
  }
  return 0;
}
```

### AI 响应（Phase 1：快速扫描）
```
📊 代码审查摘要

文件：示例代码
行数：15
严重程度分布：0 关键，2 高，1 中等，0 低

🟡 高优先级 (2)：
1. [行 2-7] 深层嵌套（4 层）
2. [行 11] 魔术数字：0.8, 1000, 0.9

🟢 中等优先级 (1)：
3. [行 4] 使用传统 for 循环而非 for...of

请求："告诉我更多关于问题 #1-2" 以获取详细信息
```

### 用户请求
```
告诉我更多关于问题 #1
```

### AI 响应（Phase 2：详细分析）
```
📋 问题 #1：深层嵌套
位置：行 2-7
严重程度：🟡 高

问题：
代码有 4 层嵌套（if → if → if → for），降低了可读性。

代码：
```javascript
if (order) {
  if (order.items) {
    if (order.items.length > 0) {
      // 主逻辑
    }
  }
}
```

影响：
- 难以理解和维护
- 认知负担高
- 容易引入错误

推荐修复：
```javascript
function processOrder(order) {
  if (!order || !order.items || order.items.length === 0) {
    return 0;
  }
  
  let total = 0;
  for (const item of order.items) {
    if (item.price) {
      total += item.price * item.quantity;
    }
  }
  
  if (total > 800) {
    total *= 0.9;
  }
  
  return total;
}
```

耗时：快速修复（5 分钟）
风险：低
```

## 示例 2：完整重构请求

### 用户请求
```
请帮我优化这段代码：
```javascript
function getUserData(userId) {
  const user = db.findUserById(userId);
  if (user) {
    const orders = db.getOrdersForUser(userId);
    if (orders && orders.length > 0) {
      const recentOrders = orders.filter(o => o.date > Date.now() - 30 * 24 * 60 * 60 * 1000);
      return {
        user: user,
        orders: recentOrders
      };
    }
    return {
      user: user,
      orders: []
    };
  }
  return null;
}
```

### AI 响应（Phase 1：快速扫描）
```
📊 代码审查摘要

严重程度分布：1 关键，2 高，0 中等，0 低

🔴 关键问题 (1)：
1. [行 16] 返回 null 导致调用者必须检查

🟡 高优先级 (2)：
2. [行 6] 魔术数字：30, 24, 60, 60, 1000
3. [行 4-14] 函数做了太多事（验证、查询、过滤、格式化）

请求："告诉我如何修复这些问题" 获取完整重构方案
```

### 用户请求
```
告诉我如何修复问题 #1, #2, #3
```

### AI 响应（Phase 3：完整重构）
```
🔧 重构计划

问题 #1, #2, #3：完整优化

当前实现：
[显示当前代码]

重构方案：
```javascript
const DAYS_IN_MILLISECONDS = 24 * 60 * 60 * 1000;
const RECENT_PERIOD_DAYS = 30;

function getUserData(userId) {
  const user = db.findUserById(userId);
  if (!user) {
    throw new UserNotFoundError(userId);
  }
  
  const orders = db.getOrdersForUser(userId);
  const recentOrders = filterRecentOrders(orders || []);
  
  return {
    user,
    orders: recentOrders
  };
}

function filterRecentOrders(orders) {
  const cutoffDate = Date.now() - (RECENT_PERIOD_DAYS * DAYS_IN_MILLISECONDS);
  return orders.filter(order => order.date > cutoffDate);
}

class UserNotFoundError extends Error {
  constructor(userId) {
    super(`User not found: ${userId}`);
    this.name = 'UserNotFoundError';
    this.userId = userId;
  }
}
```

优势：
✓ 不返回 null，避免调用者忘记检查
✓ 提取常量，提高可读性
✓ 函数职责单一（验证、查询、过滤、格式化分离）
✓ 更易于测试
✓ 更易于维护
✓ 更好的错误处理

预计耗时：20 分钟
风险：低（行为相同，结构更好）

使用建议：
```javascript
try {
  const userData = getUserData(123);
  // 使用 userData
} catch (error) {
  if (error instanceof UserNotFoundError) {
    // 处理用户不存在
  } else {
    // 处理其他错误
  }
}
```
```

## 示例 3：批量代码审查

### 用户请求
```
审查这个文件：user-service.js
```

### AI 响应（Phase 1：快速扫描）
```
📊 代码审查摘要

文件：user-service.js
行数：350
严重程度分布：2 关键，5 高，8 中等，4 低

🔴 关键问题 (2)：
1. [行 45] SQL 注入漏洞（使用字符串拼接）
2. [行 120] 密码明文存储

🟡 高优先级 (5)：
3. [行 78] 函数过长（67 行）
4. [行 150-200] 重复代码块（25 行）
5. [行 230] 类过大（350 行）
6. [行 15-35] 魔术数字散布各处
7. [行 280] 空的 catch 块

🟢 中等优先级 (8)：
8. [行 95] 变量名不清晰（d, tmp）
9. [行 180] 函数参数过多（7 个参数）
10. [行 210] 深层嵌套（5 层）
... (更多)

建议优先处理问题 #1-2（安全问题），然后是 #3-7（高优先级）

请求：
- "详细说明问题 #1" 了解 SQL 注入
- "详细说明问题 #2" 了解密码存储
- "修复问题 #1-3" 获取重构代码
```

## 渐进式披露流程图

```
用户：审查代码
    ↓
AI：Phase 1 快速扫描（~50 tokens）
    ├─ 🔴 关键：3 个问题
    ├─ 🟡 高：5 个问题
    └─ 🟢 中：8 个问题
    ↓
用户：告诉我关于问题 #1
    ↓
AI：Phase 2 详细分析（~200 tokens）
    ├─ 问题描述
    ├─ 当前代码
    ├─ 影响分析
    └─ 修复建议
    ↓
用户：如何修复问题 #1, #3, #5
    ↓
AI：Phase 3 完整重构（~500 tokens）
    ├─ 重构方案
    ├─ 完整代码
    ├─ 优势说明
    └─ 使用建议
```

## Token 消耗对比

### 一次性输出所有内容
- 完整审查报告：~2000 tokens
- 包含所有问题和详细解释
- 可能信息过载
- 浪费 token（用户可能只关注部分问题）

### 渐进式披露
- Phase 1（快速扫描）：~50 tokens
- Phase 2（详细分析）：~200 tokens/问题
- Phase 3（完整重构）：~500 tokens/问题

**示例场景：**
- 用户只关心关键问题：50 tokens（Phase 1）
- 用户需要 1 个问题的详细信息：50 + 200 = 250 tokens
- 用户需要 3 个问题的重构：50 + 600 + 1500 = 2150 tokens

**节省：**
- 如果用户只看概览，节省 1950 tokens
- 如果用户只深入 1-2 个问题，节省 1750+ tokens

## 最佳实践

### 对于代码审查者
1. 总是从 Phase 1 开始
2. 只在用户请求时进入 Phase 2/3
3. 优先显示关键和高优先级问题
4. 使用清晰的格式（表情符号、颜色）
5. 提供具体的行号引用

### 对于使用者
1. 先查看 Phase 1 摘要
2. 只请求需要详细说明的问题
3. 在准备实施时再请求重构代码
4. 按严重程度优先处理问题
5. 测试所有变更

## 常见问题

### Q: 为什么不一次性显示所有问题？
A: 渐进式披露减少 token 消耗，避免信息过载，让用户专注于最重要的问题。

### Q: 如何获取所有问题的详细分析？
A: 逐步请求："告诉我关于问题 #1", "告诉我关于问题 #2"，等等。

### Q: Phase 1 摘要包含哪些信息？
A: 文件信息、行数、严重程度分布、前 3-5 个关键/高优先级问题的简要列表。

### Q: 如何决定哪些问题需要修复？
A: 按严重程度优先：关键 > 高 > 中等 > 低。同时考虑修复的难度和影响范围。

### Q: 可以跳过某些阶段吗？
A: 可以。直接请求完整重构："请完全重构这段代码"。但不建议这样做，因为可能忽略重要上下文。

# Context Engineering

## 上下文组成

system: 系统提示词
user:   用户消息
assistant:助手消息
tool:   工具结果
tools:  工具定义

```
                 API Context
                     │
       ┌─────────────┴─────────────┐
       │                           │
   messages[]                    tools[]
       │
 ┌─────┼─────┬─────┐
 │     │     │     │
system user assistant tool
```

模型只是发出了调用请求，真正执行工具的是 Agent 框
架。这是理解 Agent 架构的关键：模型负责决策（调用什么工具、传什么参数）， Agent 框架负责执行（实际调用
API、运行代码）


## KV Cache

```
Stable Prefix
├── 固定 System Prompt
├── 固定核心规则
└── 固定核心 Tools
        ↓
Trajectory
├── User
├── Assistant
├── Tool Result
├── 状态
└── 新消息
```

把“稳定的信息”放前面，把“变化的信息”放后面。


## API


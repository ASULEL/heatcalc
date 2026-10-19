# heatcalc 网页前端

使用 Vue 3、TypeScript、Vite 和 Tailwind CSS，当前版本为 **v0.1.0**。完整功能、计算逻辑及后端启动流程见[根目录 README](../README.md)。

## 安装与启动

推荐 Node.js 24 LTS。在此目录执行：

```bash
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

打开 <http://127.0.0.1:5173/>。同时需要按根目录 README 启动 8000 端口的 Python 后端并配置模型接口。

前端当前直接请求 `http://127.0.0.1:8000/api/chat`；只启动 Vue 无法完成聊天。`--strictPort` 让 5173 被占用时直接报错，避免自动换端口后与后端允许的跨域地址不一致。

## 对话操作

- 点击“新建对话”创建，点击标题切换。
- 点击“命名”编辑标题，Enter 或移开焦点保存，Esc 取消；空名称不覆盖原名称。
- 点击“删除”移除对话，删除最后一个后自动创建空对话。
- 请求中的回复属于发起请求的对话，切换后不会串消息。
- 对话暂存在页面内存中，刷新后清空。

## 验证与构建

```bash
npm test
npm run build
```

前端测试使用 Node.js 内置测试运行器，以模拟响应验证对话行为，不调用模型。构建包含 TypeScript 检查，产物输出到 `dist/`。

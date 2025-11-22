# 1688Sync Web管理控制台

这是1688Sync项目的Web管理界面，基于React + TypeScript + Material-UI构建的现代化管理控制台。

## 功能特性

### 🎯 核心功能
- **仪表板** - 实时数据统计和可视化展示
- **商品管理** - 1688商品信息的增删改查和同步管理
- **供应商管理** - 供应商信息维护和认证状态管理
- **同步任务** - 数据同步任务的创建、监控和管理
- **实时监控** - WebSocket实时数据更新和状态监控

### 🛠 技术特性
- **React 18** - 现代化前端框架
- **TypeScript** - 类型安全的开发体验
- **Material-UI** - 现代化UI组件库
- **Recharts** - 数据可视化图表
- **React Router** - 单页应用路由
- **Axios** - HTTP请求库
- **Socket.IO** - 实时通信

### 📱 响应式设计
- 支持桌面端、平板和移动端
- 自适应布局和组件
- 现代化的用户界面

## 快速开始

### 环境要求
- Node.js 16+
- npm 或 yarn
- 后端API服务运行在 http://localhost:8000

### 安装依赖
```bash
cd web-dashboard
npm install
```

### 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置API地址：
```
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000
```

### 启动开发服务器
```bash
npm start
```

或者使用预设的开发脚本：
```bash
npm run dev
```

应用将在 http://localhost:3000 启动

### 构建生产版本
```bash
npm run build
```

构建文件将输出到 `build/` 目录

## 项目结构

```
src/
├── components/          # 可复用组件
│   ├── Layout/         # 布局组件
│   ├── DataTable/      # 数据表格组件
│   ├── StatusIndicator/# 状态指示器
│   └── Charts/         # 图表组件
├── pages/              # 页面组件
│   ├── Dashboard/      # 仪表板
│   ├── Products/       # 商品管理
│   └── SyncTasks/      # 同步任务
├── hooks/              # 自定义Hooks
│   ├── useApi.ts       # API调用Hook
│   └── useWebSocket.ts # WebSocket Hook
├── services/           # 服务层
│   ├── api.ts          # API服务
│   └── websocket.ts    # WebSocket服务
├── types/              # TypeScript类型定义
│   └── index.ts        # 主要类型定义
└── utils/              # 工具函数
```

## 主要组件说明

### MainLayout
主布局组件，包含：
- 响应式侧边导航
- 顶部工具栏
- 用户菜单
- 通知中心

### DataTable
数据表格组件，支持：
- 排序和分页
- 行选择
- 自定义操作按钮
- 搜索和筛选
- 数据导出

### StatusIndicator
状态指示器组件，提供：
- 同步状态显示
- 商品状态显示
- 供应商认证状态
- 进度条显示

### Charts
图表组件库，包含：
- 柱状图 (CustomBarChart)
- 折线图 (CustomLineChart)
- 饼图 (CustomPieChart)
- 面积图 (CustomAreaChart)
- 统计卡片 (StatCard)

## API集成

### RESTful API
通过 `src/services/api.ts` 与后端API通信：
- 商品管理 API
- 供应商管理 API
- 同步任务 API
- 仪表板统计 API

### WebSocket实时通信
通过 `src/services/websocket.ts` 实现实时更新：
- 同步进度更新
- 任务状态变化
- 系统状态监控
- 数据变更通知

## 开发指南

### 添加新页面
1. 在 `src/pages/` 创建页面组件
2. 在 `src/App.tsx` 添加路由
3. 在 `MainLayout` 添加导航项

### 添加新组件
1. 在 `src/components/` 创建组件
2. 导出组件到 `src/components/index.ts`
3. 添加TypeScript类型定义

### 自定义主题
编辑 `src/App.tsx` 中的 `theme` 配置：
- 颜色主题
- 字体设置
- 组件样式
- 响应式断点

## 部署说明

### 生产环境配置
1. 设置正确的环境变量
2. 配置API服务器地址
3. 构建生产版本
4. 部署到Web服务器

### Docker部署
```dockerfile
FROM node:16-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 故障排除

### 常见问题
1. **API连接失败** - 检查后端服务是否运行
2. **WebSocket连接失败** - 确认WebSocket服务已启动
3. **页面空白** - 检查浏览器控制台错误信息
4. **样式异常** - 清除浏览器缓存

### 调试技巧
- 使用React Developer Tools
- 检查Network面板的API请求
- 查看Console的错误信息
- 使用WebSocket调试工具

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License

# GICS Demo 部署指南

## 架构

| 组件 | 平台 | 地址 |
|------|------|------|
| 前端 | GitHub Pages | https://sunlongxu.github.io/GICS_demo/ |
| 后端 API | Render (免费) | https://gics-demo-api.onrender.com |

## 一、部署后端（Render）

1. 登录 [Render](https://render.com)，**New → Blueprint**
2. 连接 GitHub 仓库 `SunLongxu/GICS_demo`
3. 使用仓库根目录的 `render.yaml` 创建服务 `gics-demo-api`
4. 首次构建约 10–20 分钟（需安装 PyTorch）；完成后访问  
   https://gics-demo-api.onrender.com/test 应返回 JSON success

> 若 Render 服务名不同，请在 GitHub 仓库 **Settings → Secrets and variables → Actions → Variables** 设置：
> - `VITE_API_BASE_URL` = `https://你的服务.onrender.com/api`
> - `VITE_WS_BASE_URL` = `https://你的服务.onrender.com`

## 二、部署前端（GitHub Pages）

1. 仓库 **Settings → Pages → Build and deployment**
2. Source 选 **GitHub Actions**
3. 推送 `main`/`master` 分支，工作流 `.github/workflows/deploy-pages.yml` 会自动发布

或手动触发：**Actions → Deploy GitHub Pages → Run workflow**

## 三、本地开发

```bash
# 后端
cd backend/ICSGNN && source venv/bin/activate && python run_api.py

# 前端（代理到本地 API）
cd frontend && npm install && npm run dev
```

## 四、错误提示

前端所有 API / 网络失败统一显示：**network error**

## 五、搜索容错

- 作者名支持模糊匹配；仍找不到时使用默认种子节点，尽量返回子图
- 空查询、错误拼写通常仍能看到图

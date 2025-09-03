# 在 IDE 中调试 TextSnap 前端代码

本指南将帮助你在 IDE 中设置和调试 React 前端项目。

## 前提条件

- 确保已安装 Node.js 和 npm
- 确保后端服务已在本地运行（默认端口：7861）

## 步骤 1：安装依赖

首先，在项目目录中安装所有必要的依赖：

```bash
# 在 testsnap-react 目录下运行
cd f:\ysh_loc_office\projects\practice\TextSnap\flask_react\testsnap-react
npm install
```

## 步骤 2：启动开发服务器

使用 Vite 的开发服务器来启动前端应用：

```bash
npm run dev
```

这将在 http://localhost:5173 启动开发服务器（默认端口）。

## 步骤 3：在 IDE 中设置断点

### Visual Studio Code 示例

1. 打开项目文件夹 `f:\ysh_loc_office\projects\practice\TextSnap\flask_react\testsnap-react`
2. 打开你想要调试的文件，例如 `src/App.jsx`
3. 在你想要暂停执行的行号旁边点击，设置断点（会出现一个红色圆点）

### 设置示例断点位置

在以下关键位置设置断点以了解应用流程：

1. `handleUploadFile` 函数开始处（处理文件上传）
2. `handleProcessFile` 函数开始处（处理已上传的文件）
3. 轮询进度的 `checkProgress` 函数内部

## 步骤 4：启动调试会话

### 在 VS Code 中：

1. 点击左侧的调试图标（虫子图标）
2. 点击顶部的下拉菜单，选择 "创建 launch.json 文件"
3. 选择 "Web App (Chrome)" 或你使用的浏览器
4. 修改生成的 launch.json 文件如下：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "chrome",
      "request": "launch",
      "name": "启动 Chrome 调试",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}",
      "sourceMaps": true,
      "sourceMapPathOverrides": {
        "webpack:///src/*": "${webRoot}/src/*"
      }
    }
  ]
}
```

5. 点击绿色的播放按钮开始调试

## 步骤 5：使用浏览器开发者工具

除了 IDE 调试外，你还可以使用浏览器的开发者工具进行调试：

1. 在浏览器中打开 http://localhost:5173
2. 按 F12 打开开发者工具
3. 切换到 "Sources" 或 "源代码" 标签
4. 在左侧文件树中找到 `src/App.jsx` 和其他组件文件
5. 设置断点并使用控制台查看变量值

## 调试常见场景示例

### 调试文件上传流程

1. 在 `handleUploadFile` 函数开始处设置断点
2. 在应用界面点击上传按钮并选择一个文件
3. 代码执行将在断点处暂停，查看变量值和执行流程

```javascript
// 在以下代码行设置断点
handleUploadFile = async (uploadedFile) => {
    setFile(uploadedFile);
    setStatus('uploading');
    // ...其他代码
}
```

### 调试进度轮询

1. 在轮询进度的代码块中设置断点

```javascript
// 在以下代码行设置断点
const checkProgress = setInterval(async () => {
    try {
        const progResponse = await fetch(`http://localhost:7861/api/task/progress/${task_id}`);
        // ...其他代码
    }
    // ...其他代码
}, 1000);
```

## 调试技巧

1. **使用 console.log 输出信息**：在关键点添加临时日志，帮助追踪执行流程

```javascript
console.log('文件类型:', isPdf ? 'PDF' : '图片');
console.log('任务ID:', task_id);
```

2. **使用 React DevTools**：安装浏览器扩展 React DevTools，可以查看组件状态和属性

3. **监控网络请求**：在浏览器开发者工具的 "Network" 标签中，监控与后端的 API 通信

## 注意事项

1. 确保后端服务已启动，否则前端应用无法正常工作
2. 调试时可能需要刷新页面或重新上传文件来触发断点
3. 如果遇到源映射问题，可能需要检查 Vite 配置

## 常见问题排查

- **端口冲突**：如果 5173 端口被占用，可以修改 package.json 中的 dev 脚本，添加 --port 参数
  ```json
  "scripts": {
    "dev": "vite --port 5174",
    ...
  }
  ```

- **后端连接失败**：确保后端服务在 http://localhost:7861 运行，可以通过访问 http://localhost:7861/api/health 检查
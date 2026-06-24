/**
 * Electron 启动脚本
 *
 * 问题背景：Claude Code 运行时设置了 ELECTRON_RUN_AS_NODE 环境变量，
 * 会导致 electron.exe 进入 Node REPL 模式而非窗口模式，因此需要先删除该变量再启动。
 *
 * 启动流程：
 *   npm run dev:electron → 本脚本 → 删除 ELECTRON_RUN_AS_NODE → 执行 electron.exe
 */
const { spawn } = require('child_process');
const path = require('path');

// 复制当前环境变量，删除 ELECTRON_RUN_AS_NODE
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

// electron.exe 路径
const electronExe = path.join(__dirname, '..', 'node_modules', 'electron', 'dist', 'electron.exe');

// 启动 electron 主进程
const child = spawn(electronExe, ['src-electron/main.js'], {
  env,
  stdio: 'inherit',  // 将主进程的输出（stdout/stderr）传递给当前终端
  cwd: path.join(__dirname, '..'),
});

child.on('close', (code) => {
  // Electron 退出时同步退出当前进程
  process.exit(code || 0);
});

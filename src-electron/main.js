/**
 * Electron 主进程入口
 * - 创建无边框窗口
 * - 开发环境加载 Vite 开发服务器，生产环境加载打包后的文件
 */
const { app, BrowserWindow, Menu, globalShortcut, ipcMain } = require('electron');

// 隐藏默认菜单栏（File/Edit/View）
Menu.setApplicationMenu(null);
const path = require('path');

// 判断是否为开发环境
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow = null;

/** 创建主窗口 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,          // 隐藏原生标题栏，使用自定义
    titleBarStyle: 'hidden',  // macOS 专用，隐藏标题栏
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,   // 启用上下文隔离（安全）
      nodeIntegration: false,    // 禁用 Node 集成（安全）
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');  // 开发环境：Vite 开发服务器
  } else {
    // 生产环境：加载 Vite 打包后的文件
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }

  // 默认开启调试面板（底部位置）
  mainWindow.webContents.openDevTools({ mode: 'bottom' });

  // 注册全局快捷键：Ctrl+Shift+I 切换调试面板
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools();
    } else {
      mainWindow.webContents.openDevTools({ mode: 'bottom' });
    }
  });

  // 窗口控制 IPC 通信
  ipcMain.on('minimize-window', () => {
    mainWindow?.minimize();
  });
  ipcMain.on('maximize-window', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });
  ipcMain.on('close-window', () => {
    mainWindow?.close();
  });
  ipcMain.handle('is-maximized', () => {
    return mainWindow?.isMaximized() ?? false;
  });
  ipcMain.on('start-dragging', (e) => {
    // 用于标题栏拖拽区域
    if (e.sender.isDestroyed()) return;
    const bounds = e.sender.getWebContents().getOSChunkSize();
    mainWindow?.setPosition(
      mainWindow.getPosition()[0],
      mainWindow.getPosition()[1]
    );
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 应用准备就绪后创建窗口
app.whenReady().then(() => {
  createWindow();
});

// 所有窗口关闭时退出（macOS 除外）
app.on('window-all-closed', () => {
  // 卸载所有全局快捷键
  globalShortcut.unregisterAll();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// macOS：dock 图标点击时重新创建窗口
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

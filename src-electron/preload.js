const { contextBridge, ipcRenderer } = require('electron');

// 暴露给前端的 API
contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => 'http://127.0.0.1:18000/api',
  isDev: process.env.NODE_ENV === 'development',
  // 窗口控制
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  maximizeWindow: () => ipcRenderer.send('maximize-window'),
  closeWindow: () => ipcRenderer.send('close-window'),
  isMaximized: () => ipcRenderer.invoke('is-maximized'),
  // 支持拖拽区域通知
  startDragging: () => ipcRenderer.send('start-dragging'),
});

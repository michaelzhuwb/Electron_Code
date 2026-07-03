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
  // Webview 内容注入
  webviewInsertCSS: (webContentsId, css, styleId) => ipcRenderer.invoke('webview-insert-css', { webContentsId, css, styleId }),
  webviewRemoveCSS: (webContentsId, styleId) => ipcRenderer.invoke('webview-remove-css', { webContentsId, styleId }),
  webviewExecuteJS: (webContentsId, code) => ipcRenderer.invoke('webview-execute-js', { webContentsId, code }),
  onWebviewAttached: (callback) => {
    const listener = (_event, webContentsId) => callback(webContentsId);
    ipcRenderer.on('webview-attached', listener);
    return () => ipcRenderer.removeListener('webview-attached', listener);
  },
  webviewGetId: () => ipcRenderer.invoke('webview-get-id'),
});

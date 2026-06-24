const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => 'http://127.0.0.1:18000/api',
  isDev: process.env.NODE_ENV === 'development',
});

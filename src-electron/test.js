// test electron module in main process
const fs = require('fs');
const log = (msg) => fs.writeFileSync('electron-debug.log', msg + '\n', { flag: 'a' });

log('process.execPath: ' + process.execPath);
log('process.platform: ' + process.platform);
log('require electron type: ' + typeof require('electron'));
log('app global: ' + typeof app);
log('BrowserWindow global: ' + typeof BrowserWindow);

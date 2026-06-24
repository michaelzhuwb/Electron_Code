import { app, BrowserWindow } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import http from 'http';

const isDev = process.env.NODE_ENV === 'development';

let pythonProcess: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function waitForBackend(url: string, maxAttempts = 30, delay = 1000): Promise<void> {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const tryConnect = () => {
      attempts++;
      console.log(`Waiting for backend at ${url}... (attempt ${attempts}/${maxAttempts})`);

      const req = http.get(url, { timeout: 2000 }, (res) => {
        if (res.statusCode === 200) {
          console.log('Backend is ready!');
          resolve();
        } else {
          retry();
        }
        res.resume();
      });

      req.on('error', retry);
      req.on('timeout', () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      if (attempts >= maxAttempts) {
        reject(new Error(`Backend did not respond after ${maxAttempts} attempts`));
      } else {
        setTimeout(tryConnect, delay);
      }
    };

    tryConnect();
  });
}

async function startPythonBackend() {
  const backendDir = isDev
    ? path.join(__dirname, '../../backend')
    : path.join(process.resourcesPath, 'backend');

  const pythonCmd = isDev ? 'python' : path.join(process.resourcesPath, 'python', 'python.exe');

  console.log(`Starting Python backend in: ${backendDir}`);

  pythonProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'main:app', '--port', '18000', '--host', '127.0.0.1'], {
    cwd: backendDir,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python: ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python ERR: ${data.toString().trim()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
  });

  // Wait for backend to be ready
  await waitForBackend('http://127.0.0.1:18000/api/health');
}

// Check if backend is already running (dev mode)
async function checkBackendRunning(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:18000/api/health', { timeout: 2000 }, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

app.whenReady().then(async () => {
  // In dev mode: check if backend is already running, don't auto-start
  // In prod mode: auto-start the Python backend
  if (!isDev) {
    try {
      await startPythonBackend();
    } catch (error) {
      console.error('Failed to start backend:', error);
      app.quit();
      return;
    }
  } else {
    const backendRunning = await checkBackendRunning();
    if (backendRunning) {
      console.log('Dev: Backend already running');
    } else {
      console.log('Dev: Backend not running. Please start it separately:');
      console.log('  cd backend && python -m uvicorn main:app --port 18000 --host 127.0.0.1 --reload');
    }
  }

  createWindow();
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
  }
});

<template>
  <!-- AI 助手聊天界面：聊天消息 + 文件预览 + 输入框 -->
  <div class="chat-container">
    <!-- 聊天消息区域 -->
    <div class="chat-messages" ref="messageContainer">
      <!-- 无消息时的空状态提示 -->
      <div v-if="messages.length === 0" class="empty-state">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>开始对话，支持上传图片或文本文档</p>
      </div>
      <!-- 渲染所有历史消息 -->
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="message-avatar">
          <el-icon :size="24" v-if="msg.role === 'user'"><User /></el-icon>
          <el-icon :size="24" v-else><ChatDotRound /></el-icon>
        </div>
        <div class="message-content">
          <!-- 消息中的文件附件预览 -->
          <div v-if="msg.files" class="message-files">
            <div v-for="(f, fi) in msg.files" :key="fi" class="file-preview">
              <img v-if="f.is_image" :src="f.data" :alt="f.name" class="file-image" @click="previewImage(f.data)" />
              <div v-else class="file-chip">
                <el-icon><Document /></el-icon>
                <span>{{ f.name }}</span>
              </div>
            </div>
          </div>
          <!-- 消息内容，用 marked 渲染为 Markdown HTML -->
          <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          <!-- Token 用量统计 -->
          <div v-if="msg.usage" class="message-meta">
            Tokens: {{ msg.usage.total_tokens }}
          </div>
        </div>
      </div>
      <!-- 加载状态：流式输出或加载中指示器 -->
      <div v-if="loading" class="message assistant">
        <div class="message-avatar">
          <el-icon :size="24"><ChatDotRound /></el-icon>
        </div>
        <div class="message-content">
          <!-- 有流式内容时渲染，否则显示加载动画 -->
          <div v-if="streamContent" class="message-text" v-html="renderMarkdown(streamContent)"></div>
          <el-icon v-else class="typing-indicator"><Loading /></el-icon>
        </div>
      </div>
    </div>

    <!-- 待发送的文件预览区 -->
    <div v-if="pendingFiles.length > 0" class="file-preview-area">
      <div v-for="(f, idx) in pendingFiles" :key="idx" class="preview-item">
        <img v-if="f.is_image" :src="f.data" class="preview-thumb" />
        <div v-else class="preview-chip">
          <el-icon><Document /></el-icon>
          <span>{{ f.name }}</span>
        </div>
        <el-icon class="preview-remove" @click="removeFile(idx)"><Close /></el-icon>
      </div>
    </div>

    <!-- 输入区域：文件上传按钮 + 文本框 + 发送按钮 -->
    <div class="chat-input">
      <div class="input-actions">
        <input
          ref="fileInputRef"
          type="file"
          multiple
          accept="image/*,.txt,.md,.csv,.json,.py,.js,.ts,.html,.css,.xml,.log"
          style="display: none"
          @change="handleFileSelect"
        />
        <el-button :icon="Upload" circle plain @click="fileInputRef?.click()" title="上传文件" />
        <!-- Agent 模式开关 -->
        <el-button :icon="RefreshRight" circle plain @click="clearChat" title="新建对话" />
        <el-switch
          v-model="agentMode"
          size="small"
          inline-prompt
          active-text="Agent"
          inactive-text=""
          class="agent-switch"
        />
        <!-- 联网搜索开关：开启后 Agent 可自动调用 search_web -->
        <el-switch
          v-model="enableWebSearch"
          size="small"
          inline-prompt
          active-text="联网"
          inactive-text=""
          class="agent-switch"
        />
      </div>
      <el-input
        v-model="inputText"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 6 }"
        placeholder="输入消息... (Shift+Enter 换行)"
        @keydown="handleKeydown"
      />
      <el-button type="primary" :icon="Promotion" :loading="loading || uploading" @click="sendMessage">
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue';
import { ChatDotRound, User, Loading, Promotion, Upload, Document, Close, RefreshRight } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { marked } from 'marked';
import { sendChat, sendChatStream, uploadFile, agentChat } from '@/api/chat';
import type { ChatMessage, UploadedFile } from '@/api/chat';

// 消息列表和用户输入
const messages = ref<ChatMessage[]>([]);
const inputText = ref('');

// Agent 模式开关（支持工具调用）
const agentMode = ref(true);

// 联网搜索开关（开启后 Agent 可自动调用 search_web 工具，持久化到 localStorage）
const enableWebSearch = ref(localStorage.getItem('enableWebSearch') === 'true');
watch(enableWebSearch, (val) => {
  localStorage.setItem('enableWebSearch', String(val));
});

// 加载状态
const loading = ref(false);      // 正在请求
const uploading = ref(false);     // 正在上传文件
const streamContent = ref('');    // SSE 流式输出缓冲区

// DOM 引用
const messageContainer = ref<HTMLElement>();
const fileInputRef = ref<HTMLInputElement>();
const pendingFiles = ref<UploadedFile[]>([]);  // 待发送的文件列表

// localStorage 键名
const STORAGE_KEY = 'deepseek-chat-messages';

/** 保存聊天记录到 localStorage（不保存文件内容，只保留元信息） */
const saveMessages = () => {
  const toSave = messages.value.map(m => {
    if (m.files) {
      return { ...m, files: m.files.map((f: UploadedFile) => ({ name: f.name, is_image: f.is_image, is_text: f.is_text, size: f.size })) };
    }
    return m;
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
};

/** 从 localStorage 恢复聊天记录 */
const loadMessages = () => {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      messages.value = JSON.parse(saved);
    } catch {
      // ignore
    }
  }
};

onMounted(loadMessages);

/** 将 Markdown 文本渲染为 HTML，支持纯文本和多模态内容块 */
const renderMarkdown = (content: string | any[]) => {
  // 多模态内容（文本+图片块）提取文本部分
  if (Array.isArray(content)) {
    return content.map(c => c.text || '').join('\n');
  }
  if (!content) return '';
  return marked.parse(content, { async: false }) as string;
};

/** 自动滚动到消息底部 */
watch([messages, loading, streamContent], () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
    }
  });
  saveMessages();
}, { deep: true });

/** 键盘事件：Enter 发送，Shift+Enter 换行 */
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

/** 新窗口打开图片预览 */
const previewImage = (url: string | undefined) => {
  if (!url) return;
  const w = window.open('');
  if (w) {
    w.document.title = '图片预览';
    w.document.body.style.margin = '0';
    w.document.body.innerHTML = `<img src="${url}" style="max-width:100%;display:block;margin:0 auto" />`;
  }
};

/** 处理文件选择：上传到后端获取 base64/文本数据 */
const handleFileSelect = async (e: Event) => {
  const files = (e.target as HTMLInputElement).files;
  if (!files) return;

  uploading.value = true;
  for (const file of Array.from(files)) {
    try {
      const res = await uploadFile(file);
      pendingFiles.value.push(res.data.data);
    } catch (err: any) {
      ElMessage.error(err.message || '上传失败');
    }
  }
  uploading.value = false;
  // 清空 file input，允许重复选择同一文件
  if (fileInputRef.value) fileInputRef.value.value = '';
};

/** 新建对话：清空聊天记录 */
const clearChat = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有聊天记录吗？', '新建对话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    messages.value = [];
    localStorage.removeItem(STORAGE_KEY);
    ElMessage.success('已清空聊天记录');
  } catch {
    // 用户取消
  }
};

/** 移除待发送的文件 */
const removeFile = (idx: number) => {
  pendingFiles.value.splice(idx, 1);
};

/** 发送消息：根据 Agent 模式选择不同处理流程 */
const sendMessage = async () => {
  const text = inputText.value.trim();
  const hasFiles = pendingFiles.value.length > 0;
  if (!text && !hasFiles || loading.value || uploading.value) return;

  // 组装消息内容
  let content: string | any[];
  if (hasFiles) {
    content = [];
    const images = pendingFiles.value.filter(f => f.is_image);
    const textFiles = pendingFiles.value.filter(f => f.is_text && f.text);

    if (textFiles.length > 0) {
      const fileText = textFiles.map(f => `[${f.name}]\n${f.text}`).join('\n\n');
      content.push({ type: 'text', text: text ? `${text}\n\n${fileText}` : fileText });
    } else {
      content.push({ type: 'text', text });
    }

    for (const img of images) {
      content.push({ type: 'image_url', image_url: { url: img.data! } });
    }
  } else {
    content = text;
  }

  // 添加用户消息到列表
  const userMsg: ChatMessage = {
    role: 'user',
    content,
    files: hasFiles ? pendingFiles.value : undefined,
  };
  messages.value.push(userMsg);
  inputText.value = '';
  pendingFiles.value = [];
  loading.value = true;
  streamContent.value = '';

  try {
    if (agentMode.value) {
      // ============ Agent 模式：调用 /chat/agent 端点 ============
      // 构建历史消息列表（只保留纯文本，agent 不支持多模态）
      const history = messages.value.slice(0, -1).map(m => ({
        role: m.role,
        content: typeof m.content === 'string' ? m.content : (m.content as any[]).map(c => c.text || '').join('\n'),
      })) as ChatMessage[];

      const currentMsg = typeof content === 'string' ? content : (content as any[]).map(c => c.text || '').join('\n');
      const res = await agentChat(currentMsg, history, { enable_web_search: enableWebSearch.value });
      const data = res.data.data;

      // 如果有工具调用结果，拼接工具信息到回复前面
      if (data.tool_calls) {
        const toolInfo = data.tool_calls.map((tc: any) =>
          `[调用工具: ${tc.name}] 参数: ${JSON.stringify(tc.arguments)}`
        ).join('\n');
        streamContent.value = `**工具调用：**\n\`\`\`json\n${toolInfo}\n\`\`\`\n\n${data.content}`;
      } else {
        streamContent.value = data.content;
      }

      messages.value.push({
        role: 'assistant',
        content: streamContent.value,
        usage: data.usage,
      });
    } else {
      // ============ 普通模式：流式对话 ============
      const messagesData: ChatMessage[] = [...messages.value];
      const response = await sendChatStream(messagesData);

      if (!response.ok) {
        const err = await response.text();
        throw new Error(err || `HTTP ${response.status}`);
      }

      // 通过 ReadableStream 逐块读取 SSE 响应
      const reader = response.body?.getReader();
      if (!reader) throw new Error('无法读取流');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            if (data.startsWith('[ERROR]')) {
              streamContent.value += '\n' + data.slice(7);
            } else {
              streamContent.value += data;
            }
          }
        }
      }

      // 流式输出完成，将结果加入消息列表
      messages.value.push({
        role: 'assistant',
        content: streamContent.value,
      });
    }
  } catch (err: any) {
    messages.value.push({
      role: 'assistant',
      content: '请求失败: ' + (err.message || String(err)),
    });
  } finally {
    loading.value = false;
    streamContent.value = '';
  }
};
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 130px);  /* 减去侧边栏 logo + header 高度 */
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #909399;
}

.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 90%;
}

.message.user {
  align-self: flex-end;   /* 用户消息靠右 */
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;  /* AI 消息靠左 */
}

.message-avatar {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  color: #409eff;
}

.message.assistant .message-avatar {
  color: #67c23a;
}

.message-content {
  padding: 12px 16px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message.user .message-content {
  background: #409eff;
  color: #fff;
}

.message.user .message-text :deep(p) {
  color: #fff;
}

.message-files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.file-preview {
  flex-shrink: 0;
}

.file-image {
  max-width: 150px;
  max-height: 150px;
  border-radius: 6px;
  cursor: pointer;
  object-fit: cover;
}

.file-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #f0f0f0;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
}

.message.user .file-chip {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.message-text {
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.message-text :deep(pre) {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.message.user .message-text :deep(pre) {
  background: rgba(255, 255, 255, 0.15);
}

.message-text :deep(code) {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.message.user .message-text :deep(code) {
  background: rgba(255, 255, 255, 0.15);
}

.message-text :deep(p) {
  margin: 8px 0;
}

.message-text :deep(p:first-child) {
  margin-top: 0;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message-text :deep(ul), .message-text :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}

.message-text :deep(th), .message-text :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 8px;
  text-align: left;
}

.message-text :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.message-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.message.user .message-meta {
  color: rgba(255, 255, 255, 0.7);
}

.typing-indicator {
  animation: spin 1s linear infinite;
  color: #909399;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-input {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  padding-top: 0;
  align-items: flex-end;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 8px;
  padding: 10px 12px;
}

.input-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.file-preview-area {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 20px;
  padding-top: 0;
}

.preview-item {
  position: relative;
  display: flex;
  align-items: center;
}

.preview-thumb {
  height: 48px;
  border-radius: 4px;
}

.preview-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #ecf5ff;
  border-radius: 4px;
  font-size: 12px;
  color: #409eff;
}

.preview-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  cursor: pointer;
  color: #909399;
  font-size: 12px;
  background: #fff;
  border-radius: 50%;
}

.preview-remove:hover {
  color: #f56c6c;
}
</style>

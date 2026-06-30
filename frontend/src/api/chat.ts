/**
 * AI 助手（DeepSeek Chat）相关 API
 */
import request from './request';

// 聊天消息结构
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  // role=system 时为字符串；role=user/assistant 支持多模态（文本+图片）
  content: string | ContentPart[];
  files?: UploadedFile[];  // 上传的文件列表
  usage?: {  // 仅 assistant 消息有 usage 信息
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// 多模态内容块（用于 vision 图片输入）
export type ContentPart = {
  type: 'text' | 'image_url';
  text?: string;
  image_url?: { url: string };
};

// 上传文件的响应结构
export interface UploadedFile {
  name: string;           // 文件名
  content_type: string;    // MIME 类型
  data?: string;          // base64 编码（图片）
  text?: string;          // 解码后的文本（文本文件）
  is_text: boolean;        // 是否为文本文件
  is_image?: boolean;      // 是否为图片
  size: number;            // 文件大小（字节）
}

/**
 * 非流式对话（一次性返回完整结果）
 * 目前实际使用 sendChatStream 代替，此接口保留备用
 */
export const sendChat = (
  messages: ChatMessage[],
  files?: UploadedFile[],
  opts?: { temperature?: number; max_tokens?: number }
) => {
  return request.post('/chat/', { messages, files, ...opts });
};

/**
 * SSE 流式对话，逐块返回内容
 * @returns fetch Response 对象，前端通过 ReadableStream 逐块解析
 */
export const sendChatStream = (
  messages: ChatMessage[],
  files?: UploadedFile[],
  opts?: { temperature?: number; max_tokens?: number }
) => {
  // 开发环境走 Vite 代理，生产环境直接请求后端
  const url = import.meta.env.DEV ? '/api/chat/stream' : 'http://127.0.0.1:18000/api/chat/stream';
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, files, ...opts }),
  });
};

/**
 * 上传文件，返回 base64（图片）或解码文本（文本文件）
 * - 文本文件自动解码返回 text 字段
 * - 图片返回 data 字段（data URI 格式）
 */
export const uploadFile = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return request.post('/chat/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

/**
 * Agent 对话：支持工具调用（Function Calling）
 * 三步流程：用户消息 → LLM判断调用工具 → 执行工具 → LLM生成回复
 */
export const agentChat = (
  message: string,
  history: ChatMessage[],
  opts?: { temperature?: number; max_tokens?: number; enable_web_search?: boolean }
) => {
  return request.post('/chat/agent', {
    message,
    history,
    ...opts,
  });
};

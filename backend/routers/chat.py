"""DeepSeek AI 助手路由，支持普通对话、流式对话、文件上传、工具调用(Agent)"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from openai import OpenAI
from deepseek_config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL
import base64
import mimetypes
import json
from datetime import datetime

# 导入工具注册模块（Agent 功能）
from agent_tools.registry import get_tools_definitions, execute_tool

router = APIRouter(prefix="/api/chat", tags=["chat"])


# -------- 辅助模型 --------

class ImageContent(BaseModel):
    """图片内容块，用于 vision API"""
    type: str = "image_url"
    image_url: dict[str, str]


class TextContent(BaseModel):
    """文本内容块"""
    type: str = "text"
    text: str


class ChatMessage(BaseModel):
    """聊天消息结构，支持纯文本或多模态内容"""
    role: str
    # content 为字符串时是普通文本，为列表时是多模态（文本+图片）
    content: Union[str, List[Any]] = Field(..., description="消息内容 - 字符串或内容块列表")


class FileUpload(BaseModel):
    """已上传文件的数据结构（base64 编码）"""
    name: str
    content_type: str
    data: str  # base64 编码


class ChatRequest(BaseModel):
    """聊天请求体"""
    messages: List[ChatMessage]
    files: Optional[List[FileUpload]] = None  # 上传的文件列表
    model: Optional[str] = None  # 可覆盖默认模型
    temperature: Optional[float] = None  # 温度参数
    max_tokens: Optional[int] = None  # 最大 token 数


def get_client():
    """获取 OpenAI 客户端（DeepSeek 兼容 OpenAI 协议）"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DeepSeek API Key not configured")
    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_BASE,
    )


def build_message_content(content: Union[str, List[Any]], files: Optional[List[FileUpload]] = None) -> Any:
    """将用户输入和附件组装为最终的消息 content"""
    # content 为字符串时转成标准列表格式
    if isinstance(content, str):
        content_list = [{"type": "text", "text": content}]
    else:
        content_list = content

    # 追加文件内容：图片转为 data URI，文本文件显示文件名和内容
    if files:
        for f in files:
            if f.content_type.startswith("image/"):
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data"}
                })
            else:
                content_list.append({
                    "type": "text",
                    "text": f"[File: {f.name}] (uploaded)"
                })

    return content_list


# -------- 路由 --------

# POST /api/chat/ - 非流式对话（一次性返回完整结果）
@router.post("/")
def chat(request: ChatRequest):
    try:
        client = get_client()
        messages = []
        # 遍历消息列表，将 content 组装为多模态格式
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": build_message_content(msg.content),
            })

        response = client.chat.completions.create(
            model=request.model or DEEPSEEK_MODEL,
            messages=messages,
            temperature=request.temperature if request.temperature is not None else 0.7,
            max_tokens=request.max_tokens if request.max_tokens is not None else 4096,
            stream=False,
        )
        message = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        } if response.usage else None
        return {
            "code": 200,
            "data": {"content": message, "usage": usage},
            "msg": "ok",
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"code": 500, "data": None, "msg": str(e)}


# POST /api/chat/upload - 文件上传，返回 base64 或解码后的文本
@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """接收上传文件，返回 base64（图片）或解码文本（文本文件），最大 4MB"""
    try:
        contents = await file.read()
        # 文件大小限制
        if len(contents) > 4 * 1024 * 1024:
            return {"code": 400, "data": None, "msg": "文件大小不能超过4MB"}

        content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
        file_name = file.filename or "unknown"

        # 文本文件直接解码返回，文件过长时截断
        if content_type.startswith("text/"):
            try:
                text_content = contents.decode("utf-8")
                if len(text_content) > 10000:
                    text_content = text_content[:10000] + "\n\n[文件过长，已截断...]"
                return {
                    "code": 200,
                    "data": {
                        "name": file_name,
                        "content_type": content_type,
                        "text": text_content,
                        "is_text": True,
                        "size": len(contents),
                    },
                    "msg": "ok",
                }
            except UnicodeDecodeError:
                pass

        # 图片和其他二进制文件返回 base64 data URI
        b64_data = base64.b64encode(contents).decode("utf-8")
        data_url = f"data:{content_type};base64,{b64_data}"
        return {
            "code": 200,
            "data": {
                "name": file_name,
                "content_type": content_type,
                "data": data_url,
                "is_text": False,
                "is_image": content_type.startswith("image/"),
                "size": len(contents),
            },
            "msg": "ok",
        }
    except Exception as e:
        return {"code": 500, "data": None, "msg": str(e)}


# POST /api/chat/stream - SSE 流式对话，逐块返回内容
@router.post("/stream")
def chat_stream(request: ChatRequest):
    """SSE 流式响应，前端通过 ReadableStream 逐块解析渲染"""
    from fastapi.responses import StreamingResponse

    def event_stream():
        try:
            client = get_client()
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.role,
                    "content": build_message_content(msg.content),
                })

            stream = client.chat.completions.create(
                model=request.model or DEEPSEEK_MODEL,
                messages=messages,
                temperature=request.temperature if request.temperature is not None else 0.7,
                max_tokens=request.max_tokens if request.max_tokens is not None else 4096,
                stream=True,
            )
            # 逐块 yield，配合前端 SSE 解析
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============================================================
# Agent 端点：支持工具调用（Function Calling）
# ============================================================
# 核心流程：
#   1. 用户消息 + 工具定义 → DeepSeek
#   2. DeepSeek 返回 tool_call（要调用的工具名 + 参数）
#   3. 后端执行工具 → 拿到结果
#   4. 工具结果 + 完整历史 → DeepSeek
#   5. DeepSeek 生成最终自然语言回复
# ============================================================

class AgentRequest(BaseModel):
    """Agent 请求体"""
    message: str                          # 用户消息
    history: List[ChatMessage] = []       # 对话历史（不含本轮）
    model: Optional[str] = None           # 可覆盖默认模型
    temperature: Optional[float] = None   # 温度参数
    max_tokens: Optional[int] = None      # 最大 token 数


@router.post("/agent")
def agent_chat(request: AgentRequest):
    """
    Agent 端点：支持工具调用的智能对话
    如果用户意图需要调用工具，LLM 会自动调用并整合结果
    """
    try:
        client = get_client()
        tools = get_tools_definitions()

        # ---------- 第一步：构建系统提示 + 用户消息 ----------
        today = datetime.now().strftime("%Y-%m-%d")
        system_prompt = f"""你是一个专业的股票分析助手。你可以调用工具来查询数据。
当前日期：{today}（请注意使用这个日期，不要使用你训练数据中的日期）
当你需要查询数据时，请使用提供的工具。收到工具返回的结果后，用简洁自然的语言回答用户。
可用工具：
1. query_margin_data - 查询个股两融和主力资金数据
2. get_market_overview - 获取大盘涨跌停统计和涨跌幅分布
3. query_stock_m - 查询备选标的池
4. search_web - 联网搜索最新新闻、公告、市场动态等（当需要实时信息时必用）
5. 如果用户的问题不需要工具就能回答，直接回答即可"""

        # 构建完整消息列表：系统提示 + 历史 + 当前消息
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        for msg in request.history:
            messages.append({
                "role": msg.role,
                "content": msg.content if isinstance(msg.content, str) else json.dumps(msg.content, ensure_ascii=False),
            })
        messages.append({"role": "user", "content": request.message})

        # ---------- 第二次调用：带上工具定义 ----------
        response = client.chat.completions.create(
            model=request.model or DEEPSEEK_MODEL,
            messages=messages,
            tools=tools,
            temperature=request.temperature if request.temperature is not None else 0.5,  # 工具调用需要较低温度
            max_tokens=request.max_tokens if request.max_tokens is not None else 4096,
        )

        choice = response.choices[0]
        message = choice.message

        # ---------- 检查是否需要调用工具 ----------
        # 如果 assistant 返回了 tool_calls，说明 LLM 认为需要调用工具
        if message.tool_calls:
            # 提取所有工具调用（LLM 可能同时调用多个工具）
            tool_calls = message.tool_calls
            tool_results = []

            for tc in tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)

                # 执行工具
                result = execute_tool(func_name, func_args)
                tool_results.append({
                    "id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # ---------- 第三步：把工具结果喂回 LLM ----------
            # 在消息列表中追加 assistant 的 tool_call 请求
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in tool_calls
                ],
            })

            # 每条工具结果作为一条 tool 角色的消息
            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["id"],
                    "content": tr["content"],
                })

            # 第三次调用：LLM 根据工具结果生成最终回答
            final_response = client.chat.completions.create(
                model=request.model or DEEPSEEK_MODEL,
                messages=messages,
                temperature=request.temperature if request.temperature is not None else 0.5,
                max_tokens=request.max_tokens if request.max_tokens is not None else 4096,
            )

            final_message = final_response.choices[0].message.content
            final_usage = {
                "prompt_tokens": final_response.usage.prompt_tokens,
                "completion_tokens": final_response.usage.completion_tokens,
                "total_tokens": final_response.usage.total_tokens,
            } if final_response.usage else None

            return {
                "code": 200,
                "data": {
                    "content": final_message,
                    "tool_calls": [
                        {
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        }
                        for tc in tool_calls
                    ],
                    "tool_results": tool_results,
                    "usage": final_usage,
                },
                "msg": "ok",
            }

        # ---------- 没有工具调用，直接返回文本回复 ----------
        content = message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        } if response.usage else None

        return {
            "code": 200,
            "data": {"content": content, "usage": usage},
            "msg": "ok",
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"code": 500, "data": None, "msg": str(e)}

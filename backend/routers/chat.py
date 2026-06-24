"""DeepSeek AI 助手路由，支持普通对话、流式对话、文件上传"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union
from openai import OpenAI
from deepseek_config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL
import base64
import mimetypes

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

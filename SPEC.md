# hermes-volcengine-image — Hermes Agent 火山方舟生图插件

## 定位

为 Hermes Agent 提供 **火山方舟（Volcengine Ark）豆包 Seedream 生图后端**，作为 `image_gen` provider 接入。
用户通过 `image_generate` 工具即可使用 Seedream 5.0/4.5/4.0 生成图片（国内直连、中文文字渲染强、¥0.22-0.30/张）。

## 背景与动机

- Hermes 内置生图后端（FAL/OpenAI/OpenRouter/DeepInfra/Krea/xAI）均需海外代理访问
- 用户在中国大陆，需要国内直连的生图方案
- 字节 Seedream 5.0 Pro 中文小字渲染已追平 GPT Image 2，价格更低（¥0.30/张）
- GitHub 上**没有**现成的 Hermes 火山生图插件（调研确认），这是差异化空白点

## 技术要点

- 火山方舟 API 为 **OpenAI 兼容**格式：`POST https://ark.cn-beijing.volces.com/api/v3/images/generations`
- 模型 ID：`doubao-seedream-5-0-pro-260628`（5.0 Pro 最新，中文小字最强）、`doubao-seedream-5-0-260128`（5.0）、`doubao-seedream-4-5-251128`（4.5）、`doubao-seedream-4-0-250828`（4.0）
- 认证：`Authorization: Bearer <ARK_API_KEY>`
- 尺寸：支持比例预设（1:1→2048x2048、16:9→2848x1600、9:16→1600x2848、4:3、3:4 等）与 1K/2K/3K/4K
- 可选参数：`watermark`（默认 true）、`guidance_scale`、`seed`
- 响应：OpenAI 兼容 `data[].url` 或 base64

## 项目结构

```
plugins/image_gen/volcengine/
├── plugin.yaml        # name: volcengine, kind: backend, requires_env: [ARK_API_KEY]
└── __init__.py        # VolcengineImageGenProvider 实现
```

## 实现要求

### 1. 类结构

```python
class VolcengineImageGenProvider(ImageGenProvider):
    name = "volcengine"          # image_gen.provider 配置值
    display_name = "Volcengine Seedream"
```

### 2. 必须实现的方法

- `name` → `"volcengine"`
- `is_available()` → 检查 `ARK_API_KEY` 环境变量（从 `agent.secret_scope.get_secret` 读取，参考其他插件）
- `list_models()` → 返回 4 个模型目录项（5.0-pro/5.0/4.5/4.0，含 price/strengths）
- `get_setup_schema()` → 暴露 ARK_API_KEY 输入项（url: https://console.volcengine.com/ark）
- `default_model()` → `doubao-seedream-5-0-pro-260628`
- `capabilities()` → `{"modalities": ["text"], "max_reference_images": 0}`（Seedream API 不支持参考图编辑，仅文生图）
- `generate(prompt, aspect_ratio, **kwargs)` → 调 Ark API，返回 success_response/error_response

### 3. generate() 行为

1. `aspect_ratio` 映射到尺寸（用 `resolve_aspect_ratio()` 归一化后）：
   - landscape → `2848x1600`（16:9）
   - square → `2048x2048`（1:1）
   - portrait → `1600x2848`（9:16）
2. 构造请求体：`{"model": ..., "prompt": ..., "size": ..., "watermark": False}`
   - watermark 默认关（社媒配图不需要水印）；可通过 kwargs `watermark` 覆盖
3. 用 `requests.post` 调用（timeout 120s，图片生成慢）
4. 解析响应：
   - 若 `data[0].url` 存在 → 用 `save_url_image()` 下载到 `$HERMES_HOME/cache/images/`（URL 会过期）
   - 若 `data[0].b64_json` 存在 → 用 `save_b64_image()` 保存
5. 返回 `success_response(image=保存路径, model=..., prompt=..., aspect_ratio=..., provider="volcengine", modality="text")`
6. 错误处理：
   - 401 → `error_response("无效的 ARK_API_KEY", error_type="auth_error")`
   - 404/ModelNotOpen → 提示用户去火山方舟控制台开通模型
   - 超时/网络错误 → `error_type="network_error"`
   - 必须捕获所有异常，绝不抛出

### 4. 注册入口

```python
def register(ctx) -> None:
    ctx.register_image_gen_provider(VolcengineImageGenProvider())
```

### 5. 参考实现

- 骨架参考：`plugins/image_gen/openai/__init__.py`（最简 OpenAI 兼容 provider）
- API 细节参考：`https://github.com/Agents365-ai/imagencn` 的 `volcano_ark.py`（OpenAI 兼容封装）
- ABC 定义：`agent/image_gen_provider.py`（success_response/error_response/save_url_image/save_b64_image/resolve_aspect_ratio）

## 验收标准

1. `plugin.yaml` 存在且字段正确（name: volcengine, kind: backend, requires_env: [ARK_API_KEY]）
2. 代码在 Hermes 的 venv 中可 import（`python -c "import sys; sys.path.insert(0,'plugins'); from image_gen.volcengine import ..."`）
3. 单元测试（可选但加分）：mock requests 验证：
   - 正常响应 → success_response，image 是本地文件路径
   - 401 → error_response auth_error
   - 网络异常 → error_response network_error
4. 手动验收：设 `ARK_API_KEY` 后调用 provider.generate("一只戴眼镜的橘猫程序员", "square") 返回成功且图片文件存在
5. 不修改 Hermes 核心文件（run_agent.py/cli.py/gateway 等）——只新增插件目录

## 技术约束

- 纯 Python，只依赖 `requests`（Hermes venv 已有）
- 不引入新的第三方依赖
- 代码风格与现有插件一致（参考 openai/__init__.py）
- provider 名用 `volcengine`（不能叫 ark，避免与现有命名冲突）

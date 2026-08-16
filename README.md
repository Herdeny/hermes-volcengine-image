# hermes-volcengine-image

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Volcengine Ark Seedream image generation backend plugin for Hermes Agent.**

国内直连的 Hermes 生图插件：通过火山方舟豆包 Seedream 模型生成图片。
无需海外代理，中文文字渲染能力强，¥0.22–0.30/张。

A Hermes Agent `image_gen` provider backed by Volcengine Ark Doubao-Seedream.
China-direct, no proxy needed, strong Chinese text rendering, ¥0.22–0.30 per image.

## ✨ 特性 / Features

- 🖼️ **Seedream 5.0 Pro / 5.0 / 4.5 / 4.0** 四个模型，文生图
- 🇨🇳 **国内直连**（ark.cn-beijing.volces.com），无需代理
- 📝 **中文小字渲染强**——海报、社媒配图带中文标题不乱码（5.0 Pro 追平 GPT Image 2）
- 💰 **按张计费**：¥0.22–0.30/张，无订阅费
- 📐 三种比例：landscape (16:9) / square (1:1) / portrait (9:16)
- 🚫 默认无水印，可配置
- 🛡️ 完整错误处理：401 / ModelNotOpen / 超时 / 网络异常

## 📦 安装 / Install

```bash
# 1. Clone 到 Hermes 用户插件目录
git clone https://github.com/Herdeny/hermes-volcengine-image.git \
  ~/.hermes/plugins/image_gen/volcengine

# 2. 配置 API key（~/.hermes/.env）
echo "ARK_API_KEY=your-key" >> ~/.hermes/.env
```

> 项目内部自带 `plugins/image_gen/volcengine/` 目录结构，也可整体 symlink 到 `~/.hermes/plugins/`。

## 🔑 获取 API Key

1. 打开 [火山方舟控制台](https://console.volcengine.com/ark)（火山引擎账号）
2. 左侧 **API Key 管理** → 创建 API Key
3. 在 **开通管理** 中开通 `doubao-seedream-5-0-pro-260628` 模型（按量计费，新用户有免费额度）

## 🚀 使用 / Usage

### 在 Hermes 中启用

```bash
# 选择 provider（或用 hermes tools 的交互界面）
hermes config set image_gen.provider volcengine
```

然后直接让 Hermes 生图：

> 帮我生成一张图：赛博朋克风格的橘猫程序员，16:9 横版

### 支持的模型 / Models

| Model ID | Price | Notes |
|---|---|---|
| `doubao-seedream-5-0-pro-260628` | ¥0.30/张 | **默认**，最新 5.0 Pro，中文小字最强 |
| `doubao-seedream-5-0-260128` | ¥0.30/张 | 5.0，高保真 |
| `doubao-seedream-4-5-251128` | ¥0.25/张 | 4.5，均衡 |
| `doubao-seedream-4-0-250828` | ¥0.22/张 | 4.0，最便宜 |

### 比例 / Aspect Ratios

| Hermes 值 | Ark size |
|---|---|
| `landscape` | 2848×1600 (16:9) |
| `square` | 2048×2048 (1:1) |
| `portrait` | 1600×2848 (9:16) |

## 🧪 测试 / Test

```bash
python tests/test_volcengine.py    # 3 个 mock 测试（成功/401/网络异常）
```

## 📜 License

MIT

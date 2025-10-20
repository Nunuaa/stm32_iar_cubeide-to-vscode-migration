# 🚀 IAR to VSCode Migration Tool

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

**将 IAR Embedded Workbench 项目无缝迁移到 Visual Studio Code 开发环境**

[English](#english) | [中文](#中文)

</div>

---

## 中文

### 📋 项目简介

本项目提供了一套完整的工具和配置,用于将基于 **IAR Embedded Workbench** 的嵌入式项目(AT32F4xx 系列 MCU)迁移到 **Visual Studio Code** 开发环境,使用 **Clangd** 作为语言服务器,提供现代化的代码编辑体验。

**核心功能:**
- ✨ 从 IAR `.ewp` 工程文件自动提取编译配置
- 🔧 生成 Clangd 所需的 `compile_commands.json` 编译数据库
- 🎯 自动检测包含路径、宏定义和编译器选项
- 📚 提供完整的交互式配置指南
- 🚀 支持 ARM Cortex-M 系列处理器

**重要说明:** 本环境**仅用于代码编辑和浏览**,不替代 IAR 的编译和调试功能。实际的编译、链接和调试仍需使用 IAR Embedded Workbench。

---

### ✨ 主要特性

- **🎨 现代化的代码编辑体验**
  - 智能代码补全和提示
  - 精准的代码导航(跳转到定义、查找引用)
  - 强大的重构工具
  - 实时代码诊断和错误检查

- **🛠️ 自动化配置生成**
  - 自动解析 IAR 项目文件
  - 自动检测 ARM GCC 工具链的系统头文件
  - 智能处理 IAR 路径宏(`$PROJ_DIR$`, `$CONFIG_DIR$` 等)
  - 支持 Debug/Release 多配置切换

- **📦 开箱即用**
  - 详细的交互式 HTML 配置指南
  - 完善的故障排查文档
  - 清晰的输出格式便于调试
  - 无外部依赖(仅需 Python 标准库)

- **🔄 跨平台支持**
  - Windows
  - Linux
  - macOS

---

### 🚀 快速开始

#### 前置条件

1. **Visual Studio Code** - [下载地址](https://code.visualstudio.com/)
2. **Python 3.6+** - [下载地址](https://www.python.org/downloads/)
3. **ARM GCC 工具链** (arm-none-eabi) - [下载地址](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
4. **Clangd 插件** - 在 VSCode 扩展市场搜索 "clangd"

#### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/你的用户名/iar-to-vscode-migration.git
   cd iar-to-vscode-migration
   ```

2. **配置编译器路径**

   编辑 `make.py` 文件的第 18 行,修改为您的 ARM GCC 编译器路径:
   ```python
   DEFAULT_COMPILER_PATH = 'C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe'
   ```

   或者设置环境变量:
   ```bash
   # Windows (PowerShell)
   $env:COMPILER_PATH = "C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe"

   # Linux/macOS
   export COMPILER_PATH="/usr/bin/arm-none-eabi-gcc"
   ```

3. **生成编译数据库**
   ```bash
   python make.py
   ```

4. **在 VSCode 中打开项目**
   - 打开 VSCode
   - 文件 → 打开文件夹 → 选择项目目录
   - 等待 Clangd 索引完成(状态栏显示进度)

5. **重启 Clangd 语言服务器**
   - 按 `Ctrl+Shift+P` 打开命令面板
   - 输入并执行: `clangd: Restart language server`

---

### 📖 使用指南

#### 生成编译数据库

**基本用法:**
```bash
python make.py
```

**完整参数:**
```bash
python make.py --ewp <项目文件.ewp> --config <Debug|Release> --compiler <编译器路径> [--use-clang]
```

**参数说明:**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--ewp` | IAR 项目文件路径 | `T_YTL_HaoYun_144V.ewp` |
| `--config` | IAR 配置名称 (Debug/Release) | `Debug` |
| `--output` | 输出文件名 | `compile_commands.json` |
| `--compiler` | ARM GCC 编译器路径 | `E:/tool/14.2 rel1/bin/arm-none-eabi-gcc.exe` |
| `--use-clang` | 使用 Clang 模式 (更好的兼容性) | 未启用 |

**示例:**
```bash
# 生成 Debug 配置
python make.py --config Debug

# 生成 Release 配置
python make.py --config Release

# 使用自定义编译器路径
python make.py --compiler "C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe"

# 启用 Clang 模式
python make.py --use-clang
```

#### 何时需要重新生成

| 变更类型 | 需要重新生成 | 操作 |
|---------|-------------|------|
| 修改代码内容 | ❌ 否 | 无需操作 |
| 添加/删除源文件 | ✅ 是 | `python make.py` + 重启 Clangd |
| 修改包含路径 | ✅ 是 | `python make.py` + 重启 Clangd |
| 修改宏定义 | ✅ 是 | `python make.py` + 重启 Clangd |
| 切换配置 | ✅ 是 | `python make.py --config <配置名>` + 重启 Clangd |

---

### 📁 项目结构

```
iar-to-vscode-migration/
├── make.py                    # 核心脚本:生成 compile_commands.json
├── setup_guide.html           # 交互式配置指南(带进度追踪)
├── CLAUDE.md                  # Claude Code 工作指南
├── README.md                  # 本文档
├── .gitignore                 # Git 忽略规则
├── .clangd                    # Clangd 配置文件(需创建)
└── .vscode/
    └── settings.json          # VSCode 工作区配置(需创建)
```

---

### 🛠️ 配置文件说明

#### `.clangd` - Clangd 语言服务器配置

在项目根目录创建 `.clangd` 文件:
```yaml
CompileFlags:
  CompilationDatabase: "."
  Add:
    - --target=arm-none-eabi
  Remove:
    - -Wpragma-once-outside-header
    - -fno-exceptions
    - -fno-rtti

Diagnostics:
  Suppress:
    - pragma-once-outside-header
    - unused-parameter
    - unknown-pragmas
  UnusedIncludes: Strict
  MissingIncludes: Strict

Index:
  Background: Build

Completion:
  AllScopes: true
```

#### `.vscode/settings.json` - VSCode 工作区配置

在项目根目录创建 `.vscode/settings.json` 文件:
```json
{
  "clangd.arguments": [
    "--background-index",
    "--pch-storage=memory",
    "--query-driver=**/arm-none-eabi-*",
    "--compile-commands-dir=${workspaceFolder}",
    "--offset-encoding=utf-16"
  ],
  "C_Cpp.intelliSenseEngine": "Disabled",
  "files.watcherExclude": {
    "**/Debug/**": true,
    "**/.git/**": true,
    "**/build/**": true
  },
  "search.exclude": {
    "**/Debug/**": true,
    "**/.git/**": true,
    "**/build/**": true
  }
}
```

**⚠️ 重要:** 必须禁用 C/C++ 插件的 IntelliSense 以避免与 Clangd 冲突!

---

### 🔧 故障排查

#### 常见问题

<details>
<summary>❓ Clangd 没有代码补全</summary>

**可能原因:**
- `compile_commands.json` 不存在或格式错误
- Clangd 未正确安装
- C/C++ 插件冲突

**解决方案:**
1. 检查文件是否存在: `ls compile_commands.json`
2. 重新生成: `python make.py`
3. 重启 Clangd: `Ctrl+Shift+P` → `clangd: Restart language server`
4. 确认 VSCode 设置中 `C_Cpp.intelliSenseEngine` 为 `Disabled`
</details>

<details>
<summary>❓ 大量红色错误提示</summary>

**常见原因:**
- 缺少系统头文件路径
- IAR 特定语法不兼容
- 未定义的宏

**解决方案:**
1. 检查工具链检测: `python make.py` (查看输出)
2. 在 `.clangd` 中手动添加包含路径
3. 在 `.clangd` 中抑制特定警告
</details>

<details>
<summary>❓ make.py 运行失败</summary>

**错误: 找不到配置**
```bash
找不到配置 'Debug', 可用配置: Release
```
**解决:** 使用正确的配置名
```bash
python make.py --config Release
```

**错误: 编译器不存在**
```bash
[错误] 编译器路径无效
```
**解决:**
- 检查编译器路径是否正确
- 确保 ARM GCC 工具链已安装
- 使用 `--compiler` 参数指定正确路径
</details>

查看 `setup_guide.html` 获取更多详细的故障排查信息。

---

### 🎯 工作流程

1. **在 VSCode 中编辑代码**
   - 享受现代化的代码补全、跳转、重构功能
   - Clangd 提供实时错误诊断

2. **保存文件** (`Ctrl+S`)

3. **切换到 IAR 进行编译调试**
   - 在 IAR 中编译项目
   - 使用 IAR 调试器进行在线调试

**推荐:** 同时打开 VSCode 和 IAR,VSCode 负责编辑,IAR 负责编译调试。

---

### 🤝 贡献

欢迎贡献!请遵循以下步骤:

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

---

### 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

### 🙏 致谢

- [Clangd](https://clangd.llvm.org/) - LLVM 语言服务器
- [VSCode](https://code.visualstudio.com/) - 现代化的代码编辑器
- [ARM GCC](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain) - ARM GNU 工具链

---

### 📚 相关资源

- [Clangd 官方文档](https://clangd.llvm.org/)
- [Clangd 配置参考](https://clangd.llvm.org/config)
- [ARM GCC 工具链下载](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
- [VSCode Clangd 插件](https://github.com/clangd/vscode-clangd)
- [compile_commands.json 格式说明](https://clang.llvm.org/docs/JSONCompilationDatabase.html)

---

### 📞 联系方式

如有问题或建议,请:
- 提交 [Issue](https://github.com/你的用户名/iar-to-vscode-migration/issues)
- 发起 [Discussion](https://github.com/你的用户名/iar-to-vscode-migration/discussions)

---

<div align="center">

**⭐ 如果这个项目对您有帮助,请给我们一个 Star!**

Made with ❤️ by [Your Name]

</div>

---

## English

### 📋 Project Overview

This project provides a complete set of tools and configurations to migrate **IAR Embedded Workbench** based embedded projects (AT32F4xx series MCU) to **Visual Studio Code** development environment, using **Clangd** as the language server to provide a modern code editing experience.

**Core Features:**
- ✨ Automatically extract build configurations from IAR `.ewp` project files
- 🔧 Generate `compile_commands.json` compilation database for Clangd
- 🎯 Auto-detect include paths, macro definitions, and compiler options
- 📚 Provide complete interactive configuration guide
- 🚀 Support ARM Cortex-M series processors

**Important Note:** This environment is **for code editing and browsing only**, and does not replace IAR's compilation and debugging functions. Actual compilation, linking, and debugging still require IAR Embedded Workbench.

---

### 🚀 Quick Start

#### Prerequisites

1. **Visual Studio Code** - [Download](https://code.visualstudio.com/)
2. **Python 3.6+** - [Download](https://www.python.org/downloads/)
3. **ARM GCC Toolchain** (arm-none-eabi) - [Download](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
4. **Clangd Extension** - Search "clangd" in VSCode Extensions Marketplace

#### Installation Steps

1. **Clone the project**
   ```bash
   git clone https://github.com/yourusername/iar-to-vscode-migration.git
   cd iar-to-vscode-migration
   ```

2. **Configure compiler path**

   Edit line 18 of `make.py` file, change to your ARM GCC compiler path:
   ```python
   DEFAULT_COMPILER_PATH = 'C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe'
   ```

   Or set environment variable:
   ```bash
   # Windows (PowerShell)
   $env:COMPILER_PATH = "C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe"

   # Linux/macOS
   export COMPILER_PATH="/usr/bin/arm-none-eabi-gcc"
   ```

3. **Generate compilation database**
   ```bash
   python make.py
   ```

4. **Open project in VSCode**
   - Open VSCode
   - File → Open Folder → Select project directory
   - Wait for Clangd to finish indexing (progress shown in status bar)

5. **Restart Clangd language server**
   - Press `Ctrl+Shift+P` to open command palette
   - Type and execute: `clangd: Restart language server`

---

### 📖 Usage Guide

#### Generate Compilation Database

**Basic usage:**
```bash
python make.py
```

**Full parameters:**
```bash
python make.py --ewp <project.ewp> --config <Debug|Release> --compiler <compiler_path> [--use-clang]
```

**Examples:**
```bash
# Generate Debug configuration
python make.py --config Debug

# Generate Release configuration
python make.py --config Release

# Use custom compiler path
python make.py --compiler "C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe"

# Enable Clang mode
python make.py --use-clang
```

---

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

---

### 📞 Contact

For questions or suggestions, please:
- Submit an [Issue](https://github.com/yourusername/iar-to-vscode-migration/issues)
- Start a [Discussion](https://github.com/yourusername/iar-to-vscode-migration/discussions)

---

<div align="center">

**⭐ If this project helps you, please give us a Star!**

Made with ❤️ by [Your Name]

</div>

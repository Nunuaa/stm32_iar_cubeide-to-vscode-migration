# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

本项目是一个 **IAR Embedded Workbench 项目迁移工具**,用于将基于 IAR 的嵌入式项目(AT32F4xx MCU)迁移到 Visual Studio Code 开发环境,使用 Clangd 作为语言服务器提供现代化的代码编辑体验。

**核心功能:**
- 从 IAR .ewp 工程文件提取编译配置信息
- 自动生成 `compile_commands.json` 供 Clangd 使用
- 支持包含路径、宏定义、编译器选项的自动检测
- 提供完整的 VSCode + Clangd 环境配置指南

**重要说明:** 本环境**仅用于代码编辑和浏览**,不替代 IAR 的编译和调试功能。实际的编译、链接和调试仍需使用 IAR Embedded Workbench。

## 核心架构

### 1. 主要组件

#### `make.py` - 编译数据库生成脚本
这是项目的核心工具,负责从 IAR 项目文件生成 Clangd 所需的编译数据库:

**关键功能模块:**
- **XML 解析** (`extract_from_ewp`): 解析 IAR .ewp 工程文件,提取编译配置
  - 包含路径 (CCIncludePath2)
  - 宏定义 (CCDefines)
  - 编译器选项 (优化级别、语言标准等)

- **路径展开** (`expand_iar_path`): 处理 IAR 特有的路径宏
  - `$PROJ_DIR$` → 项目根目录
  - `$CONFIG_DIR$` → 配置目录 (Debug/Release)
  - `$TOOLKIT_DIR$` → IAR 工具链目录

- **工具链检测** (`detect_toolchain_includes`): 自动检测 ARM GCC 系统头文件路径
  - 查找 `arm-none-eabi/include`
  - 查找 GCC 版本特定的包含路径
  - 自动添加 `-isystem` 标志

- **文件过滤** (`filter_source_files`): 从工程文件列表中提取可编译的源文件
  - 支持 .c, .cc, .cpp, .cxx 扩展名
  - 自动排除头文件和其他非源文件

**编译标志生成规则:**
```
[编译器路径] + [CPU架构] + [语言标志] + [C/C++标准] + [优化级别] +
[警告抑制] + [宏定义] + [项目包含路径] + [系统包含路径] + [源文件]
```

**CPU 架构标志** (针对 ARM Cortex-M4):
- `-mcpu=cortex-m4`: 目标 CPU
- `-mthumb`: Thumb 指令集
- `-mfpu=fpv4-sp-d16`: 浮点单元
- `-mfloat-abi=hard`: 硬件浮点 ABI

**特殊处理:**
- 自动为 `AC_Motor_Control` 目录添加子目录 (`MotorControl/Inc`, `Common/Inc`)
- 自动为 `AT32F4_CppDrv` 目录添加 `Inc` 子目录
- 自动添加 ARM Math 库宏: `-DARM_MATH_CM4`, `-D__FPU_PRESENT=1`

#### `setup_guide.html` - 完整配置指南
交互式 HTML 文档,包含:
- VSCode 和 Clangd 安装步骤
- ARM GCC 工具链配置
- 项目配置详细说明
- 故障排查和 FAQ
- 进度追踪功能

### 2. 配置文件架构

项目使用三层配置:

#### **`.clangd`** - Clangd 语言服务器配置
```yaml
CompileFlags:
  CompilationDatabase: "."  # 使用项目根目录的 compile_commands.json
  Add:
    - --target=arm-none-eabi  # ARM 目标架构
  Remove:
    - -Wpragma-once-outside-header
    - -fno-exceptions
    - -fno-rtti

Diagnostics:
  Suppress:  # 抑制嵌入式开发常见误报
    - pragma-once-outside-header
    - unused-parameter
    - unknown-pragmas
  UnusedIncludes: Strict
  MissingIncludes: Strict

Index:
  Background: Build  # 后台索引提高性能

Completion:
  AllScopes: true  # 全作用域补全
```

#### **`.vscode/settings.json`** - VSCode 工作区配置
```json
{
  "clangd.arguments": [
    "--background-index",           // 后台索引
    "--pch-storage=memory",         // 预编译头存内存
    "--query-driver=**/arm-none-eabi-*",  // 自动查询 ARM GCC 头文件
    "--compile-commands-dir=${workspaceFolder}",
    "--offset-encoding=utf-16"
  ],
  "C_Cpp.intelliSenseEngine": "Disabled",  // ⚠️ 必须禁用避免冲突
  "files.watcherExclude": {  // 排除目录提高性能
    "**/Debug/**": true,
    "**/.git/**": true,
    "**/build/**": true
  }
}
```

#### **`compile_commands.json`** - 编译数据库
自动生成,包含每个源文件的完整编译命令。格式:
```json
[
  {
    "directory": "/path/to/source/dir",
    "command": "arm-none-eabi-gcc [flags] -c file.c -o file.o",
    "file": "/path/to/source/file.c"
  }
]
```

## 常用命令

### 生成编译数据库

**基本用法** (使用默认配置):
```bash
python make.py
```

**完整参数**:
```bash
python make.py --ewp <项目文件.ewp> --config <Debug|Release> --compiler <编译器路径> [--use-clang]
```

**参数说明:**
- `--ewp`: IAR 项目文件路径 (默认: `T_YTL_HaoYun_144V.ewp`)
- `--config`: IAR 配置名称 (默认: `Debug`, 可从环境变量 `IAR_CONFIG` 读取)
- `--output`: 输出文件名 (默认: `compile_commands.json`)
- `--compiler`: ARM GCC 编译器路径 (默认: `E:/tool/14.2 rel1/bin/arm-none-eabi-gcc.exe`)
- `--use-clang`: 使用 Clang 模式 (添加 `--target=arm-none-eabi`)

**示例:**
```bash
# 生成 Debug 配置
python make.py --config Debug

# 生成 Release 配置
python make.py --config Release

# 使用自定义编译器路径
python make.py --compiler "C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe"

# Clang 模式 (更好的兼容性)
python make.py --use-clang
```

### 重启 Clangd 语言服务器

生成 `compile_commands.json` 后**必须**重启 Clangd:

1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入并执行: `clangd: Restart language server`
3. 等待索引完成 (状态栏显示进度)

## 工作流程

### 日常开发流程

1. **在 VSCode 中编辑代码**
   - 享受现代化的代码补全、跳转、重构功能
   - Clangd 提供实时错误诊断

2. **保存文件** (`Ctrl+S`)

3. **切换到 IAR 进行编译调试**
   - 在 IAR 中编译项目
   - 使用 IAR 调试器进行在线调试

### 项目配置变更流程

**何时需要重新生成 `compile_commands.json`:**

| 变更类型 | 需要重新生成 | 命令 |
|---------|-------------|------|
| 修改代码内容 | ❌ 否 | 无需操作 |
| 添加/删除源文件 | ✅ 是 | `python make.py` + 重启 Clangd |
| 修改包含路径 | ✅ 是 | `python make.py` + 重启 Clangd |
| 修改宏定义 | ✅ 是 | `python make.py` + 重启 Clangd |
| 切换配置 (Debug/Release) | ✅ 是 | `python make.py --config <配置名>` + 重启 Clangd |

**重新生成步骤:**
```bash
# 1. 运行生成脚本
python make.py

# 2. 在 VSCode 中重启 Clangd
# Ctrl+Shift+P -> clangd: Restart language server
```

## 重要配置项

### 用户必须修改的配置

#### 1. 编译器路径 (`make.py:18`)
```python
DEFAULT_COMPILER_PATH = 'E:/tool/14.2 rel1/bin/arm-none-eabi-gcc.exe'
```
**修改为您的 ARM GCC 工具链路径:**
- Windows: `C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe`
- Linux: `/usr/bin/arm-none-eabi-gcc`
- macOS: `/opt/homebrew/bin/arm-none-eabi-gcc`

**或者使用环境变量:**
```bash
# Windows (PowerShell)
$env:COMPILER_PATH = "C:/Program Files/ARM/bin/arm-none-eabi-gcc.exe"

# Linux/macOS
export COMPILER_PATH="/usr/bin/arm-none-eabi-gcc"
```

#### 2. IAR 项目文件 (`make.py:21`)
```python
DEFAULT_EWP_FILE = 'T_YTL_HaoYun_144V.ewp'
```
修改为您的实际 IAR 项目文件名。

### CPU 架构相关配置

如果目标 MCU 不是 Cortex-M4,需要修改 `make.py:401-406` 中的 CPU 标志:

```python
# 示例: Cortex-M3
cpu_flags = [
    '-mcpu=cortex-m3',
    '-mthumb',
    # 移除 FPU 相关标志
]

# 示例: Cortex-M7 with FPU
cpu_flags = [
    '-mcpu=cortex-m7',
    '-mthumb',
    '-mfpu=fpv5-d16',
    '-mfloat-abi=hard',
]
```

## 故障排查

### 常见问题

#### 1. Clangd 没有代码补全
**可能原因:**
- `compile_commands.json` 不存在或格式错误
- Clangd 未正确安装
- C/C++ 插件冲突

**解决方案:**
```bash
# 1. 检查文件是否存在
ls compile_commands.json

# 2. 重新生成
python make.py

# 3. 重启 Clangd
# Ctrl+Shift+P -> clangd: Restart language server

# 4. 检查 VSCode 设置
# settings.json 中确保: "C_Cpp.intelliSenseEngine": "Disabled"
```

#### 2. 大量红色错误提示
**常见原因:**
- 缺少系统头文件路径
- IAR 特定语法不兼容
- 未定义的宏

**解决方案:**
1. **检查工具链检测:**
   ```bash
   python make.py  # 查看输出中的 "检测工具链系统路径" 部分
   ```

2. **手动添加包含路径** (`.clangd`):
   ```yaml
   CompileFlags:
     Add:
       - -I/path/to/missing/include
   ```

3. **抑制特定警告** (`.clangd`):
   ```yaml
   Diagnostics:
     Suppress:
       - unused-variable
       - unknown-pragmas
   ```

#### 3. make.py 运行失败

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
[错误] 编译器路径无效: 编译器不存在: E:/tool/14.2 rel1/bin/arm-none-eabi-gcc.exe
```
**解决:**
- 检查编译器路径是否正确
- Windows 路径使用正斜杠 `/` 或双反斜杠 `\\`
- 确保 ARM GCC 工具链已安装

#### 4. 找不到某些头文件
**问题:** Clangd 提示 `fatal error: 'some_header.h' file not found`

**解决步骤:**
1. 在 IAR 中检查包含路径: 项目 → Options → C/C++ Compiler → Preprocessor
2. 确认 IAR 项目已保存
3. 重新运行 `python make.py`
4. 查看输出中的 "[注意事项]" 部分,检查是否有缺失的包含路径

### 性能优化

#### Clangd 占用资源过高
**优化措施:**

1. **限制索引范围** (`.clangd`):
   ```yaml
   Index:
     Background: Skip  # 禁用后台索引
   ```

2. **排除不必要的目录** (`.vscode/settings.json`):
   ```json
   {
     "files.watcherExclude": {
       "**/Debug/**": true,
       "**/Release/**": true,
       "**/.git/**": true,
       "**/build/**": true
     }
   }
   ```

3. **限制 Clangd 线程数** (`.vscode/settings.json`):
   ```json
   {
     "clangd.arguments": [
       "--jobs=4"  // 限制为 4 个线程
     ]
   }
   ```

## 团队协作

### 应该提交到版本控制的文件

✅ **必须提交:**
- `make.py` - 生成脚本
- `.clangd` - Clangd 配置
- `.vscode/settings.json` - VSCode 工作区配置
- `setup_guide.html` - 配置指南
- `CLAUDE.md` - 本文档

❌ **不应提交:**
- `compile_commands.json` - 包含本地绝对路径,每人需自行生成
- `.vscode/*.log` - VSCode 日志文件
- `.cache/` - Clangd 缓存
- `.clangd/` - Clangd 索引数据

### `.gitignore` 建议配置

```gitignore
# 编译产物
Debug/
Release/
*.o
*.obj
*.hex
*.bin
*.elf
*.out

# IAR 特定文件
*.dep
*.ewt
*.dni
*.wsdt
*.dbgdt
settings/*.dnx

# Clangd 生成的文件
compile_commands.json
.cache/
.clangd/

# VSCode 特定
.vscode/.browse.VC.db*
.vscode/*.log

# Python 缓存
__pycache__/
*.pyc
```

### 新成员设置步骤

1. **克隆项目仓库**
2. **安装必需软件:**
   - Visual Studio Code
   - Clangd 插件 (在 VSCode 扩展市场搜索 "clangd")
   - Python 3.6+
   - ARM GCC 工具链 (arm-none-eabi)
3. **配置编译器路径:**
   - 修改 `make.py:18` 中的 `DEFAULT_COMPILER_PATH`
   - 或设置环境变量 `COMPILER_PATH`
4. **生成编译数据库:**
   ```bash
   python make.py
   ```
5. **打开 VSCode,等待 Clangd 索引完成**

## 扩展到其他项目

本工具可适配其他嵌入式项目:

### 不同的 MCU
修改 `make.py:401-406` 中的 CPU 标志:
- **Cortex-M0/M0+**: `-mcpu=cortex-m0`, `-mthumb`
- **Cortex-M3**: `-mcpu=cortex-m3`, `-mthumb`
- **Cortex-M7**: `-mcpu=cortex-m7`, `-mthumb`, `-mfpu=fpv5-d16`

### 不同的 IDE
- **Keil MDK**: 需编写类似脚本解析 `.uvprojx` 文件
- **Eclipse**: 可直接生成 `compile_commands.json`
- **CMake**: 使用 `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`

### 不同的架构
- **RISC-V**: 修改 `--target=riscv32-unknown-elf`
- **AVR**: 修改 `--target=avr`
- **MSP430**: 修改 `--target=msp430`

## 关键设计原则

### KISS (Keep It Simple)
- 脚本采用单文件设计,无外部依赖 (仅标准库)
- 配置参数集中在文件开头,方便修改
- 清晰的输出格式,便于诊断问题

### DRY (Don't Repeat Yourself)
- 路径处理统一使用 `expand_iar_path` 函数
- 编译标志生成遵循统一的顺序规则
- 去重逻辑集中在 `dedupe_preserve_order` 函数

### 可扩展性
- CPU 架构标志独立配置
- 支持通过环境变量覆盖默认值
- 宏展开机制可轻松添加新的 IAR 宏

## 参考资源

- [Clangd 官方文档](https://clangd.llvm.org/)
- [Clangd 配置参考](https://clangd.llvm.org/config)
- [ARM GCC 工具链](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
- [VSCode Clangd 插件](https://github.com/clangd/vscode-clangd)
- [compile_commands.json 格式](https://clang.llvm.org/docs/JSONCompilationDatabase.html)

---

**最后更新:** 2024
**维护者:** 项目团队
**版本:** 1.0

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取 IAR (.ewp) 工程，生成 clangd 可用的 compile_commands.json
避免手工维护包含路径与宏定义
"""

# ============================================================================
# [用户配置区域] - 请在这里修改您的编译器路径
# ============================================================================
# 
# ** 重要 ** 请修改下面的路径为您的 ARM GCC 工具链路径
# 
# Windows 示例: 'E:/tool/14.2 rel1/bin/arm-none-eabi-gcc.exe'
# Linux 示例:   '/usr/bin/arm-none-eabi-gcc'
# macOS 示例:   '/opt/homebrew/bin/arm-none-eabi-gcc'
#
DEFAULT_COMPILER_PATH = 'E:/tool/14.2 rel1/bin/arm-none-eabi-gcc.exe'

# 默认的 IAR 工程文件
DEFAULT_EWP_FILE = 'T_YTL_HaoYun_144V.ewp'

# 默认的构建配置（Debug 或 Release）
DEFAULT_CONFIGURATION = 'Debug'

# 默认输出文件名
DEFAULT_OUTPUT_FILE = 'compile_commands.json'

# ============================================================================
# 以下是程序代码，一般情况下不需要修改
# ============================================================================

import argparse
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


# ============================================================================
# 输出格式化辅助函数
# ============================================================================

def print_header(text: str):
    """打印带装饰的标题。"""
    line = "=" * 70
    print(f"\n{line}")
    print(f"  {text}")
    print(line)


def print_section(text: str):
    """打印小节标题。"""
    print(f"\n>> {text}")


def print_info(text: str, indent: int = 2):
    """打印信息。"""
    prefix = " " * indent
    print(f"{prefix}[信息] {text}")


def print_success(text: str, indent: int = 2):
    """打印成功信息。"""
    prefix = " " * indent
    print(f"{prefix}[成功] {text}")


def print_warning(text: str, indent: int = 2):
    """打印警告信息。"""
    prefix = " " * indent
    print(f"{prefix}[警告] {text}")


def print_error(text: str, indent: int = 2):
    """打印错误信息。"""
    prefix = " " * indent
    print(f"{prefix}[错误] {text}")


def print_item(text: str, indent: int = 4):
    """打印列表项。"""
    prefix = " " * indent
    print(f"{prefix}- {text}")


# ============================================================================
# 核心功能函数
# ============================================================================

def dedupe_preserve_order(items: Sequence[str]) -> List[str]:
    """保持顺序去重。"""
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def find_configuration(root: ET.Element, configuration: str) -> ET.Element:
    """从 .ewp 文件中查找指定配置(<configuration><name>XXX</name>)的节点。"""
    for cfg in root.findall("./configuration"):
        name_node = cfg.find("./name")
        if name_node is not None and (name_node.text or "").strip() == configuration:
            return cfg
    available = [
        (cfg.find("./name").text.strip() if cfg.find("./name") is not None and cfg.find("./name").text else "")
        for cfg in root.findall("./configuration")
    ]
    raise ValueError(f"找不到配置 '{configuration}'，可用配置: {', '.join([a for a in available if a]) or '无'}")


def get_option_states(configuration_node: ET.Element, settings_name: str, option_name: str) -> List[str]:
    """在 <configuration> 节点中查找 <settings><name>settings_name</name> 下 <option><name>option_name</name><state>...</state></option> 的所有 state 文本。"""
    states: List[str] = []
    for settings in configuration_node.findall("./settings"):
        settings_name_node = settings.find("./name")
        if settings_name_node is None or (settings_name_node.text or "").strip() != settings_name:
            continue
        data = settings.find("./data")
        if data is None:
            continue
        for option in data.findall("./option"):
            opt_name = option.find("./name")
            if opt_name is None or (opt_name.text or "").strip() != option_name:
                continue
            for st in option.findall("./state"):
                states.append((st.text or "").strip())
    return states


def expand_iar_path(raw_path: str, project_root: str, configuration: str, *, macro_warnings: set) -> str:
    """展开 IAR 宏(如 $PROJ_DIR$, $CONFIG_DIR$, $TOOLKIT_DIR$)并将路径转换为绝对路径。"""
    if not raw_path:
        return project_root.replace('\\', '/')

    path_str = (raw_path or "").strip().strip('"').strip("'")

    # IAR 常见宏映射
    macros = {
        'PROJ_DIR': project_root,
        'CONFIG_DIR': os.path.join(project_root, configuration),
    }
    toolkit_dir = os.environ.get('IAR_TOOLKIT_DIR') or os.environ.get('TOOLKIT_DIR')
    if toolkit_dir:
        macros['TOOLKIT_DIR'] = toolkit_dir
    else:
        # 如遇到 $TOOLKIT_DIR$ 则给出提示
        if re.search(r"\$TOOLKIT_DIR\$", path_str):
            macro_warnings.add('TOOLKIT_DIR')

    # 展开 $MACRO$
    def replace_macro(match: re.Match) -> str:
        key = match.group(1)
        if key in macros:
            return macros[key]
        macro_warnings.add(key)
        return match.group(0)  # 保留未识别的宏，后续作为缺失项报告

    path_str = re.sub(r"\$([A-Za-z0-9_]+)\$", replace_macro, path_str)

    # 以 ../ 开头：相对 project_root
    if path_str.startswith('../') or path_str.startswith('..\\'):
        abs_path = os.path.join(project_root, path_str[3:])
        return os.path.normpath(abs_path).replace('\\', '/')

    # 绝对路径直接规范化
    if os.path.isabs(path_str):
        return os.path.normpath(path_str).replace('\\', '/')

    # 其它情况：按相对于 project_root 处理
    abs_path = os.path.join(project_root, path_str)
    return os.path.normpath(abs_path).replace('\\', '/')


def extract_from_ewp(ewp_path: str, configuration: str) -> Tuple[List[str], List[str], dict]:
    """从 IAR .ewp 工程提取包含路径(CCIncludePath2)、宏定义(CCDefines)和其他编译器选项。"""
    tree = ET.parse(ewp_path)
    root = tree.getroot()

    # 查找配置节点
    config_node = find_configuration(root, configuration)

    # IAR(CC/CPP 共用)设置：ICCARM -> CCIncludePath2, CCDefines
    includes = get_option_states(config_node, 'ICCARM', 'CCIncludePath2')
    defines = get_option_states(config_node, 'ICCARM', 'CCDefines')
    
    # 提取其他编译器选项
    compiler_options = {}
    
    # C/C++ 语言标准
    cpp_dialect = get_option_states(config_node, 'ICCARM', 'IccLang')
    if cpp_dialect:
        compiler_options['cpp_dialect'] = cpp_dialect[0]
    
    # 优化级别
    optimization = get_option_states(config_node, 'ICCARM', 'CCOptLevel')
    if optimization:
        compiler_options['optimization'] = optimization[0]
    
    # 其他预处理器符号
    preprocessor_defs = get_option_states(config_node, 'ICCARM', 'PreInclude')
    if preprocessor_defs:
        compiler_options['preinclude'] = preprocessor_defs

    # 去重，保序
    return dedupe_preserve_order(includes), dedupe_preserve_order(defines), compiler_options


def extract_source_files_from_ewp(ewp_path: str) -> List[str]:
    """遍历 .ewp 工程中的文件列表(<group>/<file>/<name>)."""
    tree = ET.parse(ewp_path)
    root = tree.getroot()

    source_files: List[str] = []
    for name_node in root.findall(".//file/name"):
        text = (name_node.text or "").strip()
        if text:
            source_files.append(text)

    return source_files


def filter_source_files(raw_paths: Iterable[str]) -> List[str]:
    """仅保留可编译的 C/C++ 源文件。"""
    result: List[str] = []
    exts = ('.c', '.cc', '.cpp', '.cxx')
    for path in raw_paths:
        p = path.lower()
        if p.endswith(exts):
            result.append(path)
    return result


def detect_toolchain_includes(compiler_path: str) -> List[str]:
    """自动检测 ARM 工具链的系统包含路径。"""
    includes = []
    
    # 尝试从编译器路径推断工具链根目录
    compiler_dir = os.path.dirname(os.path.abspath(compiler_path))
    toolchain_root = os.path.dirname(compiler_dir)  # 假设编译器在 bin/ 目录下
    
    # 常见的系统包含路径
    potential_paths = [
        os.path.join(toolchain_root, 'arm-none-eabi', 'include'),
        os.path.join(toolchain_root, 'arm-none-eabi', 'include', 'c++'),
        os.path.join(toolchain_root, 'lib', 'gcc', 'arm-none-eabi'),
    ]
    
    # 检查 lib/gcc/arm-none-eabi 下的版本目录
    gcc_base = os.path.join(toolchain_root, 'lib', 'gcc', 'arm-none-eabi')
    if os.path.exists(gcc_base):
        try:
            # 查找最新的 GCC 版本目录
            versions = [d for d in os.listdir(gcc_base) if os.path.isdir(os.path.join(gcc_base, d))]
            if versions:
                # 简单排序，取最后一个（通常是最新版本）
                versions.sort()
                latest_version = versions[-1]
                potential_paths.extend([
                    os.path.join(gcc_base, latest_version, 'include'),
                    os.path.join(gcc_base, latest_version, 'include-fixed'),
                ])
        except (OSError, PermissionError):
            pass
    
    # 检查路径是否存在
    for path in potential_paths:
        if os.path.exists(path):
            includes.append(os.path.normpath(path).replace('\\', '/'))
    
    return includes


def validate_compiler(compiler_path: str) -> Tuple[bool, str]:
    """验证编译器路径是否有效。"""
    if not compiler_path:
        return False, "编译器路径为空"
    
    # 展开环境变量
    expanded_path = os.path.expandvars(compiler_path)
    
    if not os.path.exists(expanded_path):
        return False, f"编译器不存在: {expanded_path}"
    
    if not os.path.isfile(expanded_path):
        return False, f"编译器路径不是文件: {expanded_path}"
    
    # Windows 下检查是否是 .exe
    if os.name == 'nt' and not expanded_path.lower().endswith('.exe'):
        exe_path = expanded_path + '.exe'
        if os.path.exists(exe_path):
            return True, exe_path
        return False, f"Windows 下找不到可执行文件: {expanded_path} (尝试添加 .exe)"
    
    return True, expanded_path


def quote_path_if_needed(path: str) -> str:
    """如果路径包含空格，则用引号括起来。"""
    if ' ' in path and not (path.startswith('"') and path.endswith('"')):
        return f'"{path}"'
    return path


def generate_compile_commands(
    project_root: str,
    *,
    ewp_path: str,
    configuration: str,
    output_file: str,
    compiler_path: str,
    use_clang: bool = False,
):
    """生成 compile_commands.json。"""
    print_header("[开始] 生成 compile_commands.json")
    
    print_section("解析工程配置")
    print_info(f"工程文件: {ewp_path}")
    print_info(f"配置名称: {configuration}")
    
    # 验证编译器路径
    is_valid, validated_path = validate_compiler(compiler_path)
    if not is_valid:
        print_error(f"编译器路径无效: {validated_path}")
        print_warning("请检查以下设置:")
        print_item("修改脚本开头的 DEFAULT_COMPILER_PATH", indent=6)
        print_item("使用 --compiler 参数指定路径", indent=6)
        print_item("设置 COMPILER_PATH 环境变量", indent=6)
        return
    compiler_path = validated_path
    print_success(f"编译器路径: {compiler_path}")
    
    includes, defines, compiler_options = extract_from_ewp(ewp_path, configuration)

    macro_warnings: set = set()
    normalized_includes: List[str] = []
    missing_includes: List[str] = []

    for inc in includes:
        expanded = expand_iar_path(inc, project_root, configuration, macro_warnings=macro_warnings)
        if not os.path.exists(expanded):
            missing_includes.append(expanded)
        normalized_includes.append(expanded.replace('\\', '/'))

    # 为每个包含路径添加标志，并自动添加常见的子目录
    include_flags = [f'-I"{inc}"' if ' ' in inc else f'-I{inc}' for inc in normalized_includes]
    
    # 自动添加 AC_Motor_Control 和 AT32F4_CppDrv 的子目录（如果存在的话）
    for inc in normalized_includes:
        # 处理 AC_Motor_Control 目录(改用 in 判断,匹配包含该名称的路径)
        if 'AC_Motor_Control' in inc:
            # 添加 MotorControl/Inc, Common/Inc 等子目录
            motor_control_subdirs = [
                os.path.join(inc, 'MotorControl', 'Inc'),
                os.path.join(inc, 'Common', 'Inc'),
                os.path.join(inc, 'MotorControl'),
                os.path.join(inc, 'Common'),
            ]
            for subdir in motor_control_subdirs:
                if os.path.exists(subdir):
                    normalized_subdir = os.path.normpath(subdir).replace('\\', '/')
                    flag = f'-I"{normalized_subdir}"' if ' ' in normalized_subdir else f'-I{normalized_subdir}'
                    if flag not in include_flags:
                        include_flags.append(flag)
        # 处理 AT32F4_CppDrv 目录(改用 in 判断,匹配包含该名称的路径)
        elif 'AT32F4_CppDrv' in inc:
            # 添加 Inc 子目录
            inc_subdir = os.path.join(inc, 'Inc')
            if os.path.exists(inc_subdir):
                normalized_subdir = os.path.normpath(inc_subdir).replace('\\', '/')
                flag = f'-I"{normalized_subdir}"' if ' ' in normalized_subdir else f'-I{normalized_subdir}'
                if flag not in include_flags:
                    include_flags.append(flag)
    
    define_flags = [f'-D{define}' for define in defines]
    define_flags.append('-DARM_MATH_CM4')
    define_flags.append('-D__FPU_PRESENT=1')
    # 自动检测工具链系统包含路径
    print_section("检测工具链系统路径")
    system_includes = detect_toolchain_includes(compiler_path)
    if system_includes:
        print_success(f"找到 {len(system_includes)} 个系统包含路径")
        for inc in system_includes[:3]:  # 显示前3个
            print_item(inc, indent=6)
        if len(system_includes) > 3:
            print_item(f"... 还有 {len(system_includes) - 3} 个", indent=6)
    else:
        print_warning("未找到工具链系统包含路径，IntelliSense 可能不完整")
    
    # 注意：-isystem 和路径之间需要空格，或者使用单独的参数
    system_include_flags = []
    for inc in system_includes:
        system_include_flags.extend(['-isystem', inc])

    # CPU 架构标志（适配 ARM Cortex-M 系列）
    cpu_flags = [
        '-mcpu=cortex-m4',
        '-mthumb',
        '-mfpu=fpv4-sp-d16',
        '-mfloat-abi=hard',
    ]
    
    # Clang 模式需要添加 target
    if use_clang:
        cpu_flags.insert(0, '--target=arm-none-eabi')
        print_info("使用 Clang 模式 (--target=arm-none-eabi)")
    
    # 优化相关的标志（调试时建议使用 -Og）
    opt_flags = []
    if 'optimization' in compiler_options:
        opt = compiler_options['optimization']
        if opt in ['0', 'None']:
            opt_flags.append('-O0')
        elif opt in ['1', 'Low']:
            opt_flags.append('-O1')
        elif opt in ['2', 'Medium']:
            opt_flags.append('-O2')
        elif opt in ['3', 'High']:
            opt_flags.append('-O3')
    else:
        opt_flags.append('-Og')  # 默认调试优化
    
    # 嵌入式开发常用的警告抑制标志
    warning_flags = [
        '-Wno-pragma-once-outside-header',
        '-Wno-unused-parameter',
        '-Wno-unknown-pragmas',
    ]

    print_section("读取工程文件列表")
    raw_source_paths = extract_source_files_from_ewp(ewp_path)
    project_sources = filter_source_files(raw_source_paths)

    print_success(f"找到 {len(project_sources)} 个源文件 (总条目: {len(raw_source_paths)})")

    expanded_sources: List[str] = []
    missing_sources: List[str] = []

    for src in project_sources:
        expanded = expand_iar_path(src, project_root, configuration, macro_warnings=macro_warnings)
        if os.path.exists(expanded):
            expanded_sources.append(expanded.replace('\\', '/'))
        else:
            missing_sources.append(expanded)

    commands = []
    for source_file in expanded_sources:
        directory = os.path.dirname(source_file)
        obj_file = os.path.splitext(source_file)[0] + '.o'

        # 根据扩展名判断是 C++ 还是 C
        is_cpp = source_file.lower().endswith(('.cpp', '.cxx', '.cc'))
        
        # 设置语言和标准
        if is_cpp:
            lang_flag = ['-x', 'c++']
            std_flag = ['-std=c++14']  # C++ 使用 C++14
        else:
            lang_flag = ['-x', 'c']
            std_flag = ['-std=c11']    # C 使用 C11
        
        # 组合所有编译标志
        # 顺序: 编译器 -> CPU架构 -> 语言 -> 标准 -> 优化 -> 警告 -> 宏定义 -> 包含路径 -> 系统包含
        # 对 system_include_flags 中的路径进行引号处理
        quoted_system_flags = []
        for i, flag in enumerate(system_include_flags):
            if flag == '-isystem':
                quoted_system_flags.append(flag)
            else:
                quoted_system_flags.append(quote_path_if_needed(flag))
        
        command_parts = (
            [quote_path_if_needed(compiler_path)] +
            cpu_flags +
            lang_flag +
            std_flag +
            opt_flags +
            warning_flags +
            define_flags +
            include_flags +
            quoted_system_flags +
            ['-c', quote_path_if_needed(source_file), '-o', quote_path_if_needed(obj_file)]
        )

        commands.append({
            'directory': directory,
            'command': ' '.join(command_parts),
            'file': source_file,
        })

    output_path = os.path.join(project_root, output_file)
    print_section("生成编译数据库")
    print_info(f"输出文件: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(commands, f, indent=2)

    print_success(f"生成了 {len(commands)} 个编译命令")
    
    print_section("配置摘要")
    print_item(f"{len(includes)} 个包含路径")
    print_item(f"{len(defines)} 个宏定义")
    print_item(f"{len(system_includes)} 个系统包含路径")
    
    print_section("下一步操作")
    print_item("在 VS Code 中重启 clangd 语言服务器:")
    print_item("Ctrl+Shift+P -> 'clangd: Restart language server'", indent=6)

    if missing_includes:
        print_section("[注意事项]")
        print_warning("以下包含路径在文件系统中未找到 (仍已写入命令):")
        for path in missing_includes[:5]:  # 最多显示5个
            print_item(path, indent=6)
        if len(missing_includes) > 5:
            print_item(f"... 还有 {len(missing_includes) - 5} 个路径", indent=6)

    if missing_sources:
        print_section("[缺失文件]")
        print_warning("以下源文件在磁盘上不存在，已从编译数据库中排除:")
        for path in missing_sources[:5]:  # 最多显示5个
            print_item(path, indent=6)
        if len(missing_sources) > 5:
            print_item(f"... 还有 {len(missing_sources) - 5} 个文件", indent=6)

    if macro_warnings:
        print_section("[提示]")
        print_warning("检测到未展开的 IAR 宏，请设置对应环境变量:")
        for macro in sorted(macro_warnings):
            print_item(f"{macro}", indent=6)
    
    print_header("[完成!]")
    print()  # 添加一个空行


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='根据 IAR 工程 (.ewp) 生成 compile_commands.json',
        epilog='示例: python make.py --ewp M_Folklift.ewp --config Debug --use-clang',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--ewp', 
                       default=DEFAULT_EWP_FILE, 
                       help=f'IAR .ewp 工程文件路径 (默认: {DEFAULT_EWP_FILE})')
    parser.add_argument('--config', 
                       default=os.environ.get('IAR_CONFIG', DEFAULT_CONFIGURATION), 
                       help=f'IAR 配置名称 (默认: {DEFAULT_CONFIGURATION})')
    parser.add_argument('--output', 
                       default=DEFAULT_OUTPUT_FILE, 
                       help=f'输出文件名 (默认: {DEFAULT_OUTPUT_FILE})')
    parser.add_argument('--compiler', 
                       default=os.environ.get('COMPILER_PATH', DEFAULT_COMPILER_PATH), 
                       help=f'编译器路径 (默认: {DEFAULT_COMPILER_PATH})')
    parser.add_argument('--use-clang', 
                       action='store_true', 
                       help='使用 clang/clang++ 替代 arm-none-eabi-gcc')

    args = parser.parse_args()

    project_root = os.getcwd()
    ewp_path = args.ewp
    if not os.path.isabs(ewp_path):
        ewp_path = os.path.join(project_root, ewp_path)

    generate_compile_commands(
        project_root,
        ewp_path=ewp_path,
        configuration=args.config,
        output_file=args.output,
        compiler_path=args.compiler,
        use_clang=args.use_clang,
    )


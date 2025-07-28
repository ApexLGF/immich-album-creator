# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
这是一个交互式的 Immich 相册管理工具，允许用户通过交互界面管理相册和添加资源。程序启动时会要求用户输入相册导入基础路径，然后提供相册选择和资源添加功能。

## 核心架构
- **单文件结构**: 所有功能都在 `create-album.py` 中实现
- **交互式设计**: `interactive_album_manager()` - 主交互界面，处理完整的用户交互流程
- **动态配置**: 用户在运行时输入 LIBRARY_ROOT（相册导入基础路径）
- **API 交互**: 使用 Immich REST API
  - `GET /api/view/folder` - 通过相对路径获取文件夹中的 asset IDs
  - `GET /api/albums` - 获取所有相册列表
  - `POST /api/albums` - 创建新相册
  - `PUT /api/albums/{albumId}/assets` - 向现有相册添加 assets
- **路径转换逻辑**: `convert_to_immich_path()` 将本地绝对路径转换为 Immich 相对路径
- **递归资源收集**: `get_all_assets_recursive()` 收集目录及其所有子目录中的 assets

## 使用前准备

### 1. 整理本地相片目录结构
先整理好本地要导入的相片路径，将一组照片放到一个目录树中。建议按照以下结构组织：
```
/本地根目录/
├── Photo/
│   ├── Momo/
│   │   ├── 2023/
│   │   └── 2024/
│   ├── Family/
│   │   ├── 春节/
│   │   └── 旅行/
│   └── Events/
└── Videos/
```

### 2. 配置 Docker 卷映射
修改 Immich 的 `docker-compose.yml` 文件，在 `volumes` 节点增加本地目录映射：
```yaml
volumes:
  - /Volumes/LGFDATA/FamilyMemories/Photo/Momo:/mnt/test:ro
  # 更多映射示例：
  - /Users/yourname/Photos:/mnt/photos:ro
  - /path/to/your/media:/mnt/media:ro
```

### 3. 在 Immich 中导入外部目录
1. 重启 Immich 服务使卷映射生效
2. 登录 Immich Web 界面
3. 进入管理界面 → 外部库
4. 添加外部库路径，例如：`/mnt/test`
5. 触发扫描，等待 Immich 索引所有媒体文件

### 4. 运行本程序
导入完成后，即可使用本程序进行目录选择和相册管理：
- 本程序会将指定目录下的所有照片加入到选定的相册
- 不会对原有文件产生任何影响
- 建议先使用 `--dry-run` 参数测试，观察是否获取到期望的资源数量

### ⚠️ 重要提示
**路径映射关系说明：**
- 本地路径：`/Volumes/LGFDATA/FamilyMemories/Photo/Momo`
- Docker 映射：`/Volumes/LGFDATA/FamilyMemories/Photo/Momo:/mnt/test:ro`
- Immich 导入路径：`/mnt/test`
- 程序输入的基础路径：`/Volumes/LGFDATA/FamilyMemories`（本地路径）
- 程序输入的相对路径：`Photo/Momo/子文件夹`

程序会自动处理本地路径到 Immich 路径的转换，确保正确找到对应的资源。

## 常用命令

### 正常运行
```bash
python3 create-album.py        # 启动交互式相册管理工具
```

### 预览模式（推荐首次使用）
```bash
python3 create-album.py --dry-run    # 模拟操作，不实际创建或修改相册
```

### 依赖安装
```bash
pip install requests
```

## 配置要求
程序无需预先配置，所有配置信息都在运行时由用户输入：
- `IMMICH_HOST`: 程序启动时输入 Immich 服务器地址和端口（默认 127.0.0.1:2283）
- `API_KEY`: 程序启动时输入从 Immich 用户设置中获取的 API 密钥
- `LIBRARY_ROOT`: 程序启动时输入相册导入基础路径

## 交互流程
1. **服务器配置**: 输入 Immich 服务器地址（默认 127.0.0.1:2283，直接回车使用默认值）
2. **API 认证**: 输入 Immich API 密钥
3. **基础路径设置**: 输入相册导入基础路径（LIBRARY_ROOT）
4. **相册选择**: 显示现有相册列表，用户可选择现有相册或创建新相册
5. **资源路径输入**: 用户输入要添加的资源路径（相对于基础路径）
6. **验证和处理**: 自动验证路径、查询资源数量、执行操作

## 功能特性
- **零配置启动**: 程序运行时动态输入所有配置，无需修改代码
- **默认值支持**: Immich 服务器地址提供默认值 127.0.0.1:2283
- **递归资源收集**: 自动收集目录及其所有子目录中的 assets
- **路径验证**: 自动验证用户输入的路径是否存在且包含资源
- **智能去重**: 自动去除重复的 asset IDs
- **错误处理**: 完善的 API 错误处理和用户提示
- **交互式界面**: 用户友好的选择和输入界面
- **创建新相册**: 支持创建新相册并检查名称冲突
import os
import requests
import argparse

# Global variables - will be set by user input
IMMICH_HOST = None
API_KEY = None
LIBRARY_ROOT = None
HEADERS = None


def get_immich_host_from_user():
    """Get Immich host from user input with default value."""
    default_host = "127.0.0.1:2283"
    try:
        host = input(f"\n请输入 Immich 服务器地址 [{default_host}]: ").strip()
        if not host:
            host = default_host
        
        # 简单验证格式（包含端口号）
        if ':' not in host:
            print(f"警告: 地址格式可能不正确，建议格式为 IP:端口 (如 {default_host})")
            confirm = input("是否继续使用此地址? (y/n): ").strip().lower()
            if confirm != 'y':
                return get_immich_host_from_user()
        
        return host
    except KeyboardInterrupt:
        print("\n操作已取消")
        return None


def get_api_key_from_user():
    """Get API key from user input."""
    try:
        api_key = input("\n请输入 Immich API 密钥: ").strip()
        if not api_key:
            print("API 密钥不能为空")
            return get_api_key_from_user()
        
        return api_key
    except KeyboardInterrupt:
        print("\n操作已取消")
        return None


def setup_headers(api_key):
    """Setup authentication headers."""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }


def get_library_root_from_user():
    """Get library root path from user input."""
    while True:
        try:
            path = input("\n请输入相册导入基础路径 (LIBRARY_ROOT): ").strip()
            if not path:
                print("路径不能为空")
                continue
            
            # 展开用户路径（处理 ~ 等）
            full_path = os.path.expanduser(path)
            full_path = os.path.abspath(full_path)
            
            # 检查路径是否存在
            if not os.path.exists(full_path):
                print(f"路径不存在: {full_path}")
                retry = input("是否重新输入? (y/n): ").strip().lower()
                if retry != 'y':
                    return None
                continue
            
            # 检查是否为目录
            if not os.path.isdir(full_path):
                print(f"路径不是目录: {full_path}")
                retry = input("是否重新输入? (y/n): ").strip().lower()
                if retry != 'y':
                    return None
                continue
            
            return full_path
        except KeyboardInterrupt:
            print("\n操作已取消")
            return None


def convert_to_immich_path(abs_path: str) -> str:
    """Convert absolute path to Immich relative path by removing LIBRARY_ROOT prefix."""
    if LIBRARY_ROOT and abs_path.startswith(LIBRARY_ROOT):
        # Remove LIBRARY_ROOT and leading slash
        relative_path = abs_path[len(LIBRARY_ROOT):].lstrip(os.sep)
        return relative_path
    return abs_path


def get_all_subdirectories(root_dir: str):
    """Recursively get all subdirectories under root_dir."""
    subdirs = []
    for root, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            subdirs.append(os.path.join(root, dir_name))
    return subdirs


def get_folder_assets(abs_folder_path: str):
    """Retrieve asset IDs from a folder using its Immich relative path."""
    immich_path = convert_to_immich_path(abs_folder_path)
    url = f"http://{IMMICH_HOST}/api/view/folder"
    params = {"path": immich_path}

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        asset_ids = [item["id"] for item in data]
        return asset_ids
    except requests.RequestException as e:
        print(f"[ERROR] Failed to get assets for '{immich_path}': {e}")
        return []


def get_all_assets_recursive(root_folder: str):
    """Get all asset IDs from root folder and all its subdirectories."""
    all_asset_ids = []
    
    # Get assets from the root folder itself
    root_assets = get_folder_assets(root_folder)
    all_asset_ids.extend(root_assets)
    
    # Get all subdirectories and collect their assets
    subdirs = get_all_subdirectories(root_folder)
    
    for subdir in subdirs:
        subdir_assets = get_folder_assets(subdir)
        all_asset_ids.extend(subdir_assets)
        if subdir_assets:
            immich_path = convert_to_immich_path(subdir)
            print(f"  Found {len(subdir_assets)} assets in: {immich_path}")
    
    # Remove duplicates while preserving order
    unique_assets = list(dict.fromkeys(all_asset_ids))
    return unique_assets


def get_all_albums():
    """Get all albums from Immich."""
    url = f"http://{IMMICH_HOST}/api/albums"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        albums = response.json()
        return albums
    except requests.RequestException as e:
        print(f"[ERROR] Failed to get albums: {e}")
        return []


def album_exists(album_name: str):
    """Check if an album with the given name already exists."""
    albums = get_all_albums()
    return any(album.get("albumName") == album_name for album in albums)


def create_album(album_name: str, asset_ids: list, dry_run: bool):
    """Create an album if it does not already exist."""
    if album_exists(album_name):
        print(f"[SKIP] Album '{album_name}' already exists.")
        return

    if dry_run:
        print(f"[DRY-RUN] Would create album '{album_name}' with {len(asset_ids)} assets.")
        return

    url = f"http://{IMMICH_HOST}/api/albums"
    payload = {
        "albumName": album_name,
        "assetIds": asset_ids,
        "description": ""
    }

    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"[OK] Album created: {album_name} ({len(asset_ids)} assets)")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to create album '{album_name}': {e}")


def add_assets_to_album(album_id: str, asset_ids: list, dry_run: bool):
    """Add assets to an existing album."""
    if not asset_ids:
        print("[ERROR] No assets to add.")
        return False
    
    if dry_run:
        print(f"[DRY-RUN] Would add {len(asset_ids)} assets to album.")
        return True
    
    url = f"http://{IMMICH_HOST}/api/albums/{album_id}/assets"
    payload = {"ids": asset_ids}
    
    try:
        response = requests.put(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"[OK] Added {len(asset_ids)} assets to album.")
        return True
    except requests.RequestException as e:
        print(f"[ERROR] Failed to add assets to album: {e}")
        return False


def get_new_album_name():
    """Get new album name from user."""
    while True:
        try:
            album_name = input("\n请输入新相册名称: ").strip()
            if not album_name:
                print("相册名称不能为空")
                continue
            
            # 检查相册是否已存在
            if album_exists(album_name):
                print(f"相册 '{album_name}' 已存在，请使用其他名称")
                continue
            
            return album_name
        except KeyboardInterrupt:
            print("\n操作已取消")
            return None


def select_album_interactive():
    """Interactive album selection interface."""
    albums = get_all_albums()
    
    print(f"\n发现 {len(albums)} 个相册:")
    print("0. 创建新相册")
    
    for idx, album in enumerate(albums, 1):
        album_name = album.get("albumName", "未命名相册")
        asset_count = album.get("assetCount", 0)
        print(f"{idx}. {album_name} ({asset_count} 个资源)")
    
    while True:
        try:
            choice = input(f"\n请选择相册 (0-{len(albums)}): ").strip()
            if not choice:
                continue
            
            choice_num = int(choice)
            if choice_num == 0:
                # 创建新相册
                new_album_name = get_new_album_name()
                if new_album_name:
                    return {"create_new": True, "albumName": new_album_name}
                else:
                    return None
            elif 1 <= choice_num <= len(albums):
                return albums[choice_num - 1]
            else:
                print(f"请输入 0 到 {len(albums)} 之间的数字")
        except ValueError:
            print("请输入有效的数字")
        except KeyboardInterrupt:
            print("\n操作已取消")
            return None


def get_path_from_user():
    """Get path input from user with asset count validation."""
    while True:
        try:
            path = input(f"\n请输入要添加到相册的路径 (相对于基础路径):\n{LIBRARY_ROOT}/").strip()
            if not path:
                print("路径不能为空")
                continue
            
            # 构建完整路径
            full_path = os.path.join(LIBRARY_ROOT, path)
            
            # 检查路径是否存在
            if not os.path.exists(full_path):
                print(f"路径不存在: {full_path}")
                retry = input("是否重新输入? (y/n): ").strip().lower()
                if retry != 'y':
                    return None, 0
                continue
            
            # 查询该路径的资源数量
            print(f"\n正在查询路径中的资源: {full_path}")
            if os.path.isdir(full_path):
                asset_ids = get_all_assets_recursive(full_path)
            else:
                # 如果是文件，获取所在目录的资源
                asset_ids = get_folder_assets(os.path.dirname(full_path))
            
            asset_count = len(asset_ids)
            print(f"在该路径中找到 {asset_count} 个资源")
            
            # 如果没有资源，提示用户重新输入
            if asset_count == 0:
                print("⚠️  该路径中没有找到任何资源")
                retry = input("是否重新输入路径? (y/n): ").strip().lower()
                if retry != 'y':
                    return None, 0
                continue
            
            return full_path, asset_count
        except KeyboardInterrupt:
            print("\n操作已取消")
            return None, 0


def interactive_album_manager(dry_run: bool):
    """Interactive album management interface."""
    global IMMICH_HOST, API_KEY, LIBRARY_ROOT, HEADERS
    
    print("\n=== Immich 相册管理工具 ===")
    print("\n--- 配置设置 ---")
    
    # 获取 Immich 主机地址
    IMMICH_HOST = get_immich_host_from_user()
    if IMMICH_HOST is None:
        print("未设置 Immich 服务器地址，程序退出。")
        return
    
    # 获取 API 密钥
    API_KEY = get_api_key_from_user()
    if API_KEY is None:
        print("未设置 API 密钥，程序退出。")
        return
    
    # 设置请求头
    HEADERS = setup_headers(API_KEY)
    
    # 获取基础路径
    LIBRARY_ROOT = get_library_root_from_user()
    if LIBRARY_ROOT is None:
        print("未设置基础路径，程序退出。")
        return
    
    print(f"\n✓ Immich 服务器: {IMMICH_HOST}")
    print(f"✓ API 密钥: {'*' * (len(API_KEY) - 4) + API_KEY[-4:]}")
    print(f"✓ 基础路径: {LIBRARY_ROOT}")
    print("\n=== 相册资源管理 ===")
    
    # 选择相册或创建新相册
    selected_album = select_album_interactive()
    if selected_album is None:
        print("操作已取消。")
        return
    
    # 判断是创建新相册还是使用现有相册
    is_new_album = selected_album.get("create_new", False)
    album_name = selected_album.get("albumName", "未命名相册")
    
    if is_new_album:
        print(f"\n将创建新相册: {album_name}")
        album_id = None
    else:
        album_id = selected_album.get("id")
        print(f"\n已选择现有相册: {album_name}")
    
    # 获取路径和资源数量
    target_path, asset_count = get_path_from_user()
    if target_path is None:
        print("操作已取消。")
        return
    
    # 重新收集资源（因为在get_path_from_user中已经收集过了，这里可以复用）
    if os.path.isdir(target_path):
        asset_ids = get_all_assets_recursive(target_path)
    else:
        # 如果是文件，获取所在目录的资源
        asset_ids = get_folder_assets(os.path.dirname(target_path))
    
    if not asset_ids:
        print(f"在路径 {target_path} 中未找到任何资源")
        return
    
    # 执行操作
    if is_new_album:
        # 创建新相册
        success = create_album(album_name, asset_ids, dry_run)
        if success or dry_run:
            if dry_run:
                print(f"[DRY-RUN] 模拟完成：创建新相册 '{album_name}' 包含 {len(asset_ids)} 个资源")
            else:
                print(f"成功创建新相册 '{album_name}' 包含 {len(asset_ids)} 个资源")
        else:
            print("创建新相册失败")
    else:
        # 添加到现有相册
        success = add_assets_to_album(album_id, asset_ids, dry_run)
        if success:
            if dry_run:
                print(f"[DRY-RUN] 模拟完成：将 {len(asset_ids)} 个资源添加到相册 '{album_name}'")
            else:
                print(f"成功将 {len(asset_ids)} 个资源添加到相册 '{album_name}'")
        else:
            print("添加资源到相册失败")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive Immich album management tool.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without creating albums or adding assets")
    args = parser.parse_args()

    interactive_album_manager(dry_run=args.dry_run)

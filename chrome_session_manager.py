import os
import sys
import json
import time
import socket
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import shutil  # 添加到文件顶部的导入部分

class ChromeSessionManager:
    def __init__(self):
        self.sessions_file = "chrome_sessions.json"
        self.sessions = self._load_sessions()
        self._cleanup_dead_sessions()
        
    def _load_sessions(self):
        """加载已保存的会话信息"""
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_sessions(self):
        """保存会话信息到文件"""
        with open(self.sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=4)

    def _is_port_in_use(self, port):
        """检查端口是否被使用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                s.close()
                return False
            except socket.error:
                return True

    def _cleanup_dead_sessions(self):
        """清理已经不存在的会话"""
        dead_sessions = []
        for session_id, info in self.sessions.items():
            # 检查用户数据目录是否存在，而不是检查端口
            user_data_dir = info.get('user_data_dir')
            if not user_data_dir or not os.path.exists(user_data_dir):
                dead_sessions.append(session_id)
        
        for session_id in dead_sessions:
            print(f"清理无效会话: {session_id}")
            del self.sessions[session_id]
        
        if dead_sessions:
            self._save_sessions()

    def create_new_session(self, session_id=None, note=None):
        """创建新的Chrome会话"""
        if session_id is None:
            session_id = str(len(self.sessions) + 1)
            
        chrome_options = webdriver.ChromeOptions()
        
        # 创建用户数据目录
        user_data_dir = os.path.abspath(f"chrome_data/user_{session_id}")
        chrome_options.add_argument(f"user-data-dir={user_data_dir}")
        
        # 设置调试端口
        debug_port = 9222 + int(session_id)
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")
        
        # 添加性能优化选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--enable-extensions')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-site-isolation-trials')
        chrome_options.page_load_strategy = 'none'
        
        # 最多重试3次
        for attempt in range(3):
            try:
                service = Service(ChromeDriverManager().install())
                service.start()  # 显式启动服务
                
                driver = webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
                
                # 设置窗口大小和位置
                window_width = 1200
                window_height = 800
                screen_padding = 50
                
                # 计算窗口位置
                session_num = int(session_id)
                x_offset = screen_padding + ((session_num - 1) % 3) * (window_width + screen_padding)
                y_offset = screen_padding + ((session_num - 1) // 3) * (window_height + screen_padding)
                
                # 设置窗口大小和位置
                driver.set_window_size(window_width, window_height)
                driver.set_window_position(x_offset, y_offset)
                
                # 设置窗口标题
                title = f"Chrome_{session_id}"
                if note:
                    title += f" ({note})"
                driver.execute_script(f"document.title = '{title}'")
                
                # 保存会话信息
                self.sessions[session_id] = {
                    "debug_port": debug_port,
                    "user_data_dir": user_data_dir,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "last_used": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": note,
                    "position": {
                        "x": x_offset,
                        "y": y_offset,
                        "width": window_width,
                        "height": window_height
                    }
                }
                self._save_sessions()
                
                return session_id, driver
                
            except Exception as e:
                print(f"创建会话尝试 {attempt + 1}/3 失败: {e}")
                try:
                    if 'driver' in locals():
                        driver.quit()
                    if 'service' in locals():
                        service.stop()
                except:
                    pass
                
                if attempt < 2:  # 如果不是最后一次尝试
                    print("等待5秒后重试...")
                    time.sleep(5)
                else:
                    print("创建新会话失败，已达到最大重试次数")
                    return None, None

    def _create_single_session_thread(self, session_id, note=None):
        """在线程中创建单个会话"""
        session_id, driver = self.create_new_session(session_id, note)
        if driver:
            try:
                driver.set_page_load_timeout(30)
                self._do_task(session_id, driver)
                return session_id, driver
            except Exception as e:
                print(f"会话 {session_id} 打开网页时出错: {e}")
                try:
                    driver.quit()
                except:
                    pass
        return None

    def batch_create_sessions(self, count):
        """并行批量创建多个Chrome会话"""
        drivers = []
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = []
            for i in range(count):
                session_id = str(len(self.sessions) + i + 1)
                note = input(f"请为第 {session_id} 个Chrome输入备注（直接回车跳过）: ").strip()
                futures.append(executor.submit(self._create_single_session_thread, session_id, note))
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    drivers.append(result)
        
        return drivers

    def connect_to_session(self, session_id):
        """连接到现有的Chrome会话"""
        if session_id not in self.sessions:
            print(f"会话 {session_id} 不存在")
            return None
            
        session_info = self.sessions[session_id]
        debug_port = session_info['debug_port']
        user_data_dir = session_info['user_data_dir']
        
        # 只关闭我们之前创建的进程
        if 'pid' in session_info:
            try:
                if sys.platform == 'darwin':
                    os.system(f'kill -9 {session_info["pid"]}')
                    time.sleep(1)
            except:
                pass
        
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"user-data-dir={user_data_dir}")
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # 恢复窗口位置和大小
            if 'position' in session_info:
                pos = session_info['position']
                driver.set_window_size(pos.get('width', 1200), pos.get('height', 800))
                driver.set_window_position(pos['x'], pos['y'])
            else:
                # 如果没有保存位置信息，使用新的计算方法
                screen_size = driver.execute_script("""
                    return {
                        width: window.screen.availWidth,
                        height: window.screen.availHeight
                    };
                """)
                
                window_width = 1200
                window_height = 800
                screen_padding = 50
                
                max_windows_per_row = max(1, (screen_size['width'] - screen_padding) // (window_width + screen_padding))
                
                session_num = int(session_id)
                row = (session_num - 1) // max_windows_per_row
                col = (session_num - 1) % max_windows_per_row
                
                x_offset = screen_padding + col * (window_width + screen_padding)
                y_offset = screen_padding + row * (window_height + screen_padding)
                
                driver.set_window_size(window_width, window_height)
                driver.set_window_position(x_offset, y_offset)
                
                session_info['position'] = {
                    "x": x_offset,
                    "y": y_offset,
                    "width": window_width,
                    "height": window_height
                }
                self._save_sessions()
            
            # 恢复窗口标题
            title = f"Chrome_{session_id}"
            if session_info.get('note'):
                title += f" ({session_info['note']})"
            driver.execute_script(f"document.title = '{title}'")
            
            # 获取新的进程ID
            if sys.platform == 'darwin':
                cmd = f"lsof -i :{debug_port} | grep Chrome | awk '{{print $2}}'"
                pid = os.popen(cmd).read().strip().split('\n')[0]
                session_info["pid"] = pid
                self._save_sessions()
            
            return driver
        except Exception as e:
            print(f"连接到会话 {session_id} 失败: {e}")
            return None

    def _kill_chrome_process(self, port):
        """只关闭指定端口的Chrome进程"""
        try:
            if sys.platform == 'darwin':
                # 只关闭使用特定调试端口的Chrome进程
                cmd = f"lsof -i :{port} | grep Chrome | awk '{{print $2}}'"
                pids = os.popen(cmd).read().strip().split('\n')
                
                for pid in pids:
                    if pid:
                        try:
                            # 检查进程是否存在
                            if os.system(f'ps -p {pid} > /dev/null') == 0:
                                os.system(f'kill -9 {pid}')
                                print(f"已关闭 Chrome 进程 (PID: {pid})")
                        except:
                            pass
            
            elif sys.platform == 'win32':
                # Windows下的进程关闭逻辑
                pass
                
        except Exception as e:
            print(f"关闭Chrome进程时出错: {e}")
        
        time.sleep(1)  # 等待进程关闭

    def list_sessions(self):
        """列出所有保存的会话"""
        if not self.sessions:
            print("\n当前没有保存的会话")
            return
            
        print("\n现有Chrome会话:")
        for session_id, info in self.sessions.items():
            print(f"会话 ID: {session_id}")
            if info.get('note'):
                print(f"备注: {info['note']}")
            print(f"创建时间: {info['created_at']}")
            print(f"最后使用: {info.get('last_used', '未知')}")
            print(f"窗口位置: X={info.get('position', {}).get('x', '未知')} Y={info.get('position', {}).get('y', '未知')}")
            print("-" * 30)

    def _do_task(self, session_id, driver):
        """执行任务"""
        try:
            # 增加页面加载超时时间
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            try:
                driver.get("https://pump.fun")
            except TimeoutException:
                print(f"会话 {session_id} 页面加载超时，继续执行...")
            except Exception as e:
                print(f"会话 {session_id} 页面加载出错: {e}")
            
            note = self.sessions[session_id].get('note', '')
            print(f"会话 {session_id} {f'({note})' if note else ''} 开始执行任务")

            # 等待页面加载完成
            time.sleep(3)  # 添加固定等待时间

            # 最多尝试20次，每次间隔0.5秒
            for i in range(20):
                try:
                    # 尝试找到搜索框
                    search_box = driver.find_element(By.CSS_SELECTOR, '#search-token')
                    if search_box:
                        search_box.clear()
                        search_box.send_keys("CRAMvzDsSpXYsFpcoDr6vFLJMBeftez1E7277xwPpump")
                        print(f"会话 {session_id} 输入完成")
                        
                        time.sleep(0.5)  # 添加短暂延迟
                        
                        # 尝试找到并点击按钮
                        button = driver.find_element(By.CSS_SELECTOR, 'form button:nth-child(2)')
                        if button:
                            button.click()
                            print(f"会话 {session_id} 点击完成")
                            return session_id, driver
                        
                except:
                    time.sleep(0.5)  # 增加等待时间
                    continue
            
            print(f"会话 {session_id} 未找到元素")
            return session_id, driver
            
        except Exception as e:
            print(f"会话 {session_id} 执行任务时出错: {e}")
            return session_id, driver  # 返回driver而不是抛出异常

    def _restore_single_session_thread(self, session_id):
        """在线程中恢复单个会话"""
        print(f"正在恢复会话 {session_id}...")
        driver = self.connect_to_session(session_id)
        if driver:
            try:
                self._do_task(session_id, driver)
                return session_id, driver
            except Exception as e:
                print(f"会话 {session_id} 恢复时出错: {e}")
                try:
                    driver.quit()
                except:
                    pass
        return None

    def restore_all_sessions(self):
        """并行恢复所有保存的会话"""
        session_ids = list(self.sessions.keys())
        restored_drivers = []
        
        with ThreadPoolExecutor(max_workers=len(session_ids)) as executor:
            # 创建Future对象列表
            future_to_session = {
                executor.submit(self._restore_single_session_thread, session_id): session_id 
                for session_id in session_ids
            }
            
            # 获取结果
            for future in as_completed(future_to_session):
                result = future.result()
                if result:
                    restored_drivers.append(result)
        
        return restored_drivers

    def restart_session(self, session_id):
        """重启指定的Chrome会话"""
        print(f"正在重启会话 {session_id}...")
        
        # 先关闭现有的会话
        if session_id in self.sessions:
            session_info = self.sessions[session_id]
            if 'pid' in session_info:
                try:
                    if sys.platform == 'darwin':
                        os.system(f'kill -9 {session_info["pid"]}')
                        time.sleep(1)
                except:
                    pass
        
        # 重新连接会话
        driver = self.connect_to_session(session_id)
        if driver:
            try:
                driver.set_page_load_timeout(30)
                self._do_task(session_id, driver)
                return session_id, driver
            except Exception as e:
                print(f"重启会话 {session_id} 时出错: {e}")
                try:
                    driver.quit()
                except:
                    pass
        return None

    def clone_extensions(self, from_session_id, to_session_id):
        """复制插件和必要的配置"""
        if from_session_id not in self.sessions:
            print(f"源会话 {from_session_id} 不存在")
            return False
        
        if to_session_id not in self.sessions:
            print(f"目标会话 {to_session_id} 不存在")
            return False
        
        # 源目录和目标目录
        from_user_data = self.sessions[from_session_id]['user_data_dir']
        to_user_data = self.sessions[to_session_id]['user_data_dir']
        
        try:
            # 确保目标Default目录存在
            os.makedirs(os.path.join(to_user_data, 'Default'), exist_ok=True)
            
            # 1. 复制必要的文件和目录
            files_to_copy = [
                ('Default/Extensions', True),           # 插件目录 (是目录)
                ('Default/Preferences', False),         # 用户偏好
                ('Default/Secure Preferences', False),  # 安全偏好
                ('Local State', False),                # Chrome状态
            ]
            
            for (path, is_dir) in files_to_copy:
                from_path = os.path.join(from_user_data, path)
                to_path = os.path.join(to_user_data, path)
                
                if os.path.exists(from_path):
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(to_path), exist_ok=True)
                    
                    # 如果目标已存在，先删除
                    if os.path.exists(to_path):
                        if is_dir:
                            shutil.rmtree(to_path)
                        else:
                            os.remove(to_path)
                    
                    # 复制文件或目录
                    if is_dir:
                        shutil.copytree(from_path, to_path)
                    else:
                        shutil.copy2(from_path, to_path)
                    print(f"成功复制: {path}")
            
            # 2. 修改配置文件中的路径
            files_to_update = ['Preferences', 'Secure Preferences']
            for file_name in files_to_update:
                file_path = os.path.join(to_user_data, 'Default', file_name)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # 更新扩展路径
                        if 'extensions' in data:
                            # 保持扩展的启用状态
                            extensions_settings = data['extensions'].get('settings', {})
                            for ext_id, ext_data in extensions_settings.items():
                                if 'path' in ext_data:
                                    ext_data['path'] = ext_data['path'].replace(
                                        f"user_{from_session_id}",
                                        f"user_{to_session_id}"
                                    )
                        
                        # 保存修改后的文件
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2)
                        print(f"成功更新 {file_name}")
                        
                    except Exception as e:
                        print(f"更新 {file_name} 时出错: {e}")
            
            # 3. 更新 Local State 文件
            local_state_path = os.path.join(to_user_data, 'Local State')
            if os.path.exists(local_state_path):
                try:
                    with open(local_state_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    
                    # 更新扩展路径
                    if 'extensions' in state:
                        state['extensions']['settings'] = {}  # 清空旧设置
                        state['extensions']['install_signature'] = {}  # 清空安装签名
                    
                    # 保存修改后的文件
                    with open(local_state_path, 'w', encoding='utf-8') as f:
                        json.dump(state, f, indent=2)
                    print("成功更新 Local State")
                    
                except Exception as e:
                    print(f"更新 Local State 时出错: {e}")
            
            return True
        except Exception as e:
            print(f"复制插件时出错: {e}")
            return False

    def batch_clone_sessions(self, from_session_id, count):
        """批量创建新会话并复制插件"""
        if from_session_id not in self.sessions:
            print(f"源会话 {from_session_id} 不存在")
            return []
        
        # 检查源会话是否有插件
        source_extensions = os.path.join(self.sessions[from_session_id]['user_data_dir'], 'Default', 'Extensions')
        if not os.path.exists(source_extensions):
            print(f"警告: 源会话 {from_session_id} 没有安装插件")
            return []
        
        new_drivers = []
        start_id = len(self.sessions) + 1
        
        for i in range(count):
            new_session_id = str(start_id + i)
            note = input(f"请为第 {new_session_id} 个Chrome输入备注（直接回车跳过）: ").strip()
            
            print(f"正在创建会话 {new_session_id}...")
            # 创建新会话
            session_id, driver = self.create_new_session(new_session_id, note)
            if driver:
                # 先关闭driver以便复制插件
                driver.quit()
                
                print(f"正在复制插件到会话 {new_session_id}...")
                # 复制插件
                if self.clone_extensions(from_session_id, new_session_id):
                    print(f"正在重启会话 {new_session_id}...")
                    # 重新连接会话以加载插件
                    driver = self.connect_to_session(new_session_id)
                    if driver:
                        try:
                            self._do_task(new_session_id, driver)
                            new_drivers.append((new_session_id, driver))
                            print(f"会话 {new_session_id} 创建完成")
                        except Exception as e:
                            print(f"执行任务时出错: {e}")
                else:
                    print(f"会话 {new_session_id} 复制插件失败")
        
        return new_drivers

    def clear_session(self, session_id):
        """清除指定会话的进程和本地数据"""
        success = True
        session_info = None
        
        # 获取会话信息（如果存在）
        if session_id in self.sessions:
            session_info = self.sessions[session_id]
            # 1. 关闭进程
            if 'pid' in session_info:
                try:
                    if sys.platform == 'darwin':
                        os.system(f'kill -9 {session_info["pid"]}')
                except:
                    pass
        
        try:
            # 2. 删除用户数据目录（无论会话是否存在）
            user_data_dir = os.path.abspath(f"chrome_data/user_{session_id}")
            if os.path.exists(user_data_dir):
                try:
                    shutil.rmtree(user_data_dir)
                    print(f"已删除用户数据目录: {user_data_dir}")
                except Exception as e:
                    print(f"删除用户数据目录时出错: {e}")
                    success = False
            
            # 3. 从sessions中移除（如果存在）
            if session_id in self.sessions:
                del self.sessions[session_id]
                self._save_sessions()
                print(f"已从会话列表中移除会话 {session_id}")
            else:
                print(f"会话 {session_id} 不存在于会话列表中，仅清理数据")
            
            return success
        except Exception as e:
            print(f"清除会话时出错: {e}")
            return False

def show_help():
    print("""
    可用指令：
    1. new                 - 创建新的Chrome会话
    2. new [数量]          - 批量创建指定数量的Chrome会话
    3. connect [id]        - 连接到指定ID的Chrome会话
    4. restart [id]        - 重启指定ID的Chrome会话
    5. run [id]           - 重新执行指定ID的任务
    6. restore            - 恢复所有保存的会话
    7. copy [from_id] [to_id] - 复制from_id的插件到已存在的to_id会话
    8. clone [from_id] [count] - 从from_id克隆count个新会话
    9. quit [id]          - 退出指定ID的会话
    10. clear [id]        - 清除指定ID的会话数据和进程
    11. list              - 显示所有已保存的会话
    12. help              - 显示帮助信息
    13. exit              - 退出所有会话并退出程序
    """)

def main():
    manager = ChromeSessionManager()
    current_drivers = []
    
    # 启动时询问是否恢复会话
    if manager.sessions:
        print(f"\n发现 {len(manager.sessions)} 个已保存的会话")
        restore = input("是否要恢复这些会话？(y/n): ").strip().lower()
        if restore == 'y':
            current_drivers = manager.restore_all_sessions()
    
    while True:
        command = input("\n请输入指令 (输入 'help' 获取指令列表): ").strip().lower()
        
        if command.startswith("new"):
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                # 并行批量创建
                count = int(parts[1])
                print(f"正在并行创建 {count} 个Chrome会话...")
                new_drivers = manager.batch_create_sessions(count)
                current_drivers.extend(new_drivers)
            else:
                # 创建单个
                session_id, driver = manager.create_new_session()
                if driver:
                    current_drivers.append((session_id, driver))
                    try:
                        driver.set_page_load_timeout(30)
                        manager._do_task(session_id, driver)
                    except Exception as e:
                        print(f"打开网页时出错: {e}")
                        print("请手动在浏览器中输入网址: https://pump.fun")
            
        elif command.startswith("connect"):
            parts = command.split()
            if len(parts) != 2:
                print("请指定会话ID，例如: connect 1")
                continue
                
            session_id = parts[1]
            driver = manager.connect_to_session(session_id)
            if driver:
                current_drivers.append((session_id, driver))
                try:
                    driver.set_page_load_timeout(30)
                    manager._do_task(session_id, driver)
                except Exception as e:
                    print(f"打开网页时出错: {e}")
                    print("请手动在浏览器中输入网址: https://pump.fun")
        
        elif command.startswith("restart"):
            parts = command.split()
            if len(parts) != 2:
                print("请指定会话ID，例如: restart 1")
                continue
            
            session_id = parts[1]
            # 从current_drivers中移除旧的driver
            current_drivers = [(sid, drv) for sid, drv in current_drivers if sid != session_id]
            
            # 重启会话
            result = manager.restart_session(session_id)
            if result:
                current_drivers.append(result)
                print(f"会话 {session_id} 已重启")
        
        elif command.startswith("run"):
            parts = command.split()
            if len(parts) != 2:
                print("请指定会话ID，例如: run 1")
                continue
            
            session_id = parts[1]
            # 查找对应的driver
            driver = None
            for sid, drv in current_drivers:
                if sid == session_id:
                    driver = drv
                    break
            
            if driver:
                try:
                    manager._do_task(session_id, driver)
                    print(f"会话 {session_id} 任务执行完成")
                except Exception as e:
                    print(f"执行任务时出错: {e}")
            else:
                print(f"未找到会话 {session_id} 的活动窗口，请先使用 connect 或 restart 命令")
        
        elif command == "restore":
            new_drivers = manager.restore_all_sessions()
            current_drivers.extend(new_drivers)
            
        elif command == "list":
            manager.list_sessions()
            
        elif command == "help":
            show_help()
            
        elif command.startswith("copy"):
            parts = command.split()
            if len(parts) != 3:
                print("请使用正确的格式: copy [from_id] [to_id]")
                continue
            
            from_id = parts[1]
            to_id = parts[2]
            
            # 复制到现有会话
            if manager.clone_extensions(from_id, to_id):
                # 从current_drivers中移除目标会话的driver
                current_drivers = [(sid, drv) for sid, drv in current_drivers if sid != to_id]
                # 重新连接会话以加载插件
                driver = manager.connect_to_session(to_id)
                if driver:
                    current_drivers.append((to_id, driver))
                    try:
                        manager._do_task(to_id, driver)
                    except Exception as e:
                        print(f"执行任务时出错: {e}")
        
        elif command.startswith("clone"):
            parts = command.split()
            if len(parts) != 3:
                print("请使用正确的格式: clone [from_id] [count]")
                continue
            
            from_id = parts[1]
            if not parts[2].isdigit():
                print("请输入有效的数量")
                continue
                
            count = int(parts[2])
            new_drivers = manager.batch_clone_sessions(from_id, count)
            current_drivers.extend(new_drivers)
        
        elif command.startswith("quit"):
            parts = command.split()
            if len(parts) != 2:
                print("请指定会话ID，例如: quit 1")
                continue
            
            session_id = parts[1]
            # 查找并关闭指定的driver
            for sid, drv in current_drivers[:]:  # 使用切片创建副本进行迭代
                if sid == session_id:
                    try:
                        drv.quit()
                        print(f"已退出会话 {session_id}")
                    except Exception as e:
                        print(f"退出会话 {session_id} 时出错: {e}")
                    current_drivers.remove((sid, drv))
                    break
            else:
                print(f"未找到活动的会话 {session_id}")
        
        elif command.startswith("clear"):
            parts = command.split()
            if len(parts) != 2:
                print("请指定会话ID，例如: clear 1")
                continue
            
            session_id = parts[1]
            # 先从current_drivers中移除并关闭driver
            for sid, drv in current_drivers[:]:
                if sid == session_id:
                    try:
                        drv.quit()
                    except:
                        pass
                    current_drivers.remove((sid, drv))
                    break
            
            # 清除会话数据
            if manager.clear_session(session_id):
                print(f"会话 {session_id} 已完全清除")
            else:
                print(f"清除会话 {session_id} 时出现错误")
        
        elif command == "exit":
            for _, driver in current_drivers:
                try:
                    driver.quit()
                except:
                    pass
            print("退出程序...")
            break
            
        else:
            print("无效指令，请重新输入。")

if __name__ == "__main__":
    main() 
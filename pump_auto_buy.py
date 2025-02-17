import os
import time
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

class PumpAutoBuyApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pump Auto Buy")
        self.driver = None  # 添加driver作为类属性
        
        # 获取可执行文件所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe运行
            self.app_dir = os.path.dirname(sys.executable)
        else:
            # 如果是python脚本运行
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            
        # 设置配置文件路径
        self.config_file = os.path.join(self.app_dir, "settings.json")
        
        # 确保配置文件存在
        if not os.path.exists(self.config_file):
            with open(self.config_file, "w") as f:
                json.dump({}, f)
        
        # 设置窗口在屏幕中央
        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算窗口位置
        window_width = 420
        window_height = 280
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置窗口样式
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=6)
        style.configure("TEntry", padding=6)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 合约地址输入
        ttk.Label(main_frame, text="Token Contract Address:").grid(row=0, column=0, sticky=tk.W)
        self.contract_entry = ttk.Entry(main_frame, width=40)
        self.contract_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # SOL数量输入
        ttk.Label(main_frame, text="SOL Amount:").grid(row=2, column=0, sticky=tk.W)
        self.sol_amount_entry = ttk.Entry(main_frame, width=40)
        self.sol_amount_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 开始按钮
        ttk.Button(main_frame, text="Start Auto Buy", command=self.start_auto_buy).grid(row=4, column=0, columnspan=2, pady=20)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=5, column=0, columnspan=2)
        
        # 配置列的权重
        main_frame.columnconfigure(0, weight=1)
        
        # 加载保存的设置
        self.load_settings()
        
        # 绑定关闭窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def load_settings(self):
        """从配置文件加载设置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    settings = json.load(f)
                self.contract_entry.insert(0, settings.get("contract_address", ""))
                self.sol_amount_entry.insert(0, settings.get("sol_amount", ""))
                print(f"Settings loaded from {self.config_file}")
        except Exception as e:
            print(f"Error loading settings: {e}")
            
    def save_settings(self):
        """保存设置到配置文件"""
        try:
            settings = {
                "contract_address": self.contract_entry.get().strip(),
                "sol_amount": self.sol_amount_entry.get().strip()
            }
            with open(self.config_file, "w") as f:
                json.dump(settings, f)
            print(f"Settings saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def on_closing(self):
        """窗口关闭时保存设置并关闭浏览器"""
        self.save_settings()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()
        
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.config(text=message)
        self.root.update()
        
    def validate_sol_amount(self, amount_str):
        """验证SOL数量输入是否有效"""
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("SOL amount must be greater than 0")
            return True, amount
        except ValueError as e:
            return False, str(e)
            
    def start_auto_buy(self):
        """开始自动购买流程"""
        contract_address = self.contract_entry.get().strip()
        sol_amount = self.sol_amount_entry.get().strip()
        
        # 验证输入
        if not contract_address:
            messagebox.showerror("Error", "Please enter token contract address")
            return
            
        is_valid, result = self.validate_sol_amount(sol_amount)
        if not is_valid:
            messagebox.showerror("Error", f"Invalid SOL amount: {result}")
            return
            
        self.update_status("Launching browser...")
        self.root.update()
        
        try:
            # 如果已经有浏览器实例在运行，先关闭它
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            # 打开浏览器
            self.driver = open_chrome("https://pump.fun")
            
            # 处理初始弹窗
            self.update_status("Handling initial popup...")
            if not handle_initial_popup(self.driver):
                print("No popup found, please handle manually if needed")
                
            # 等待钱包连接
            self.update_status("Please connect your wallet in the browser...")
            if not wait_for_wallet_connection(self.driver):
                self.update_status("Wallet connection failed")
                return
                
            # 执行购买
            self.update_status("Executing purchase...")
            if auto_buy_token(self.driver, contract_address, result):
                self.update_status("Purchase completed")
            else:
                self.update_status("Purchase failed")
                
        except Exception as e:
            self.update_status(f"Error occurred: {str(e)}")
            
    def run(self):
        """运行应用"""
        self.root.mainloop()

def open_chrome(url):
    chrome_options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    return driver

def handle_initial_popup(driver):
    """处理初始的弹窗"""
    try:
        # 等待页面加载完成
        time.sleep(2)
        
        # 处理 Cookie 设置
        try:
            accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='btn-accept-all']"))
            )
            accept_button.click()
            print("Accepted cookie settings")
            time.sleep(1)
        except:
            print("No cookie settings found, continuing")
        
        # 处理 I'm ready to pump 弹窗
        selectors = [
            "//div[@role='dialog']//button",        # 通过对话框中的按钮
        ]
        
        ready_button = None
        for selector in selectors:
            try:
                ready_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"Found button using selector: {selector}")
                break
            except:
                continue
                
        if ready_button:
            ready_button.click()
            print("Confirmed initial popup")
            return True
        else:
            print("No popup button found")
            return False
            
    except Exception as e:
        print(f"Error handling initial popup: {e}")
        return False

def wait_for_wallet_connection(driver):
    """等待用户连接钱包并确认连接成功"""
    try:
        # 设置等待时间为1天（24小时 = 86400秒）
        wait = WebDriverWait(driver, 86400)
        
        # 等待连接钱包按钮出现并可点击
        connect_button = wait.until(
            EC.presence_of_element_located((By.XPATH, "/html/body/nav/div[2]/button"))
        )
        print("Please connect your wallet...")
        
        # 等待钱包连接成功（通过检查 view profile 文字是否出现）
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'view profile')]"))
        )
        print("Wallet connected successfully!")
        return True
    except Exception as e:
        print(f"Wallet connection timeout or error: {e}")
        return False

def search_and_select_token(driver, contract_address):
    """搜索并选择代币"""
    try:
        # 等待搜索输入框可用
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='search-token']"))
        )
        search_input.clear()
        search_input.send_keys(contract_address)
        time.sleep(1)  # 等待输入完成
        
        # 点击搜索按钮
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/main/div/div[2]/form/button"))
        )
        search_button.click()
        time.sleep(2)  # 等待搜索结果加载
        
        # 等待搜索结果并点击
        try:
            # 使用更通用的选择器：找到搜索结果区域中的第一个结果
            first_result = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//main//div[contains(@class, 'grid')]//a[1]/div"))
            )
            first_result.click()
            print("Token selected")
            return True
        except Exception as e:
            print(f"No search results found: {e}")
            # 尝试备用选择器
            try:
                first_result = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//main//div[contains(@class, 'overflow-hidden')]//a[1]/div"))
                )
                first_result.click()
                print("Token selected using backup selector")
                return True
            except:
                print("No results found with backup selector")
                return False
            
    except Exception as e:
        print(f"Error searching for token: {e}")
        return False

def auto_buy_token(driver, contract_address, sol_amount):
    """自动购买代币"""
    try:
        # 先搜索并选择代币
        if not search_and_select_token(driver, contract_address):
            return False
            
        time.sleep(2)  # 等待页面加载
            
        # 等待SOL输入框可用
        sol_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[@id='amount']"))
        )
        sol_input.clear()  # 清除默认值
        sol_input.send_keys(str(sol_amount))  # 输入SOL数量
        time.sleep(1)  # 等待输入完成
        
        # 等待并点击购买按钮
        buy_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/main/div/div[1]/div[2]/div/div/div[5]"))
        )
        buy_button.click()
        
        print("Purchase initiated")
        return True
    except Exception as e:
        print(f"Error during purchase: {e}")
        return False

if __name__ == "__main__":
    app = PumpAutoBuyApp()
    app.run()

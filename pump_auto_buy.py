import os
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

CONFIG_FILE = "pump_settings.json"

class PumpAutoBuyApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pump Auto Buy")
        self.root.geometry("420x280")  # 增加窗口高度
        
        # 设置窗口样式
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=6)
        style.configure("TEntry", padding=6)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 合约地址输入
        ttk.Label(main_frame, text="代币合约地址:").grid(row=0, column=0, sticky=tk.W)
        self.contract_entry = ttk.Entry(main_frame, width=40)
        self.contract_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # SOL数量输入
        ttk.Label(main_frame, text="购买SOL数量:").grid(row=2, column=0, sticky=tk.W)
        self.sol_amount_entry = ttk.Entry(main_frame, width=40)
        self.sol_amount_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 开始按钮
        ttk.Button(main_frame, text="开始自动购买", command=self.start_auto_buy).grid(row=4, column=0, columnspan=2, pady=20)
        
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
        """加载保存的设置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    settings = json.load(f)
                    self.contract_entry.insert(0, settings.get('contract_address', ''))
                    self.sol_amount_entry.insert(0, settings.get('sol_amount', '3'))
            else:
                # 如果配置文件不存在，使用默认值
                self.sol_amount_entry.insert(0, '3')
        except Exception as e:
            print(f"加载设置时出错: {e}")
            # 使用默认值
            self.sol_amount_entry.insert(0, '3')
            
    def save_settings(self):
        """保存当前设置"""
        try:
            settings = {
                'contract_address': self.contract_entry.get().strip(),
                'sol_amount': self.sol_amount_entry.get().strip()
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"保存设置时出错: {e}")
            
    def on_closing(self):
        """窗口关闭时保存设置"""
        self.save_settings()
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
                raise ValueError("SOL数量必须大于0")
            return True, amount
        except ValueError as e:
            return False, str(e)
        
    def start_auto_buy(self):
        """开始自动购买流程"""
        contract_address = self.contract_entry.get().strip()
        sol_amount = self.sol_amount_entry.get().strip()
        
        # 验证输入
        if not contract_address:
            messagebox.showerror("错误", "请输入代币合约地址")
            return
            
        is_valid, result = self.validate_sol_amount(sol_amount)
        if not is_valid:
            messagebox.showerror("错误", f"SOL数量无效: {result}")
            return
            
        self.update_status("正在启动浏览器...")
        self.root.update()
        
        try:
            # 打开浏览器
            driver = open_chrome("https://pump.fun")
            
            # 处理初始弹窗
            self.update_status("处理初始弹窗...")
            if not handle_initial_popup(driver):
                print("没有点击弹窗，需要请自己处理")
                # driver.quit()
                # self.update_status("初始弹窗处理失败")
                # return
                
            # 等待钱包连接
            self.update_status("请在浏览器中连接钱包...")
            if not wait_for_wallet_connection(driver):
                driver.quit()
                self.update_status("钱包连接失败")
                return
                
            # 执行购买
            self.update_status("正在执行购买...")
            if auto_buy_token(driver, contract_address, result):
                self.update_status("购买操作已完成")
            else:
                self.update_status("购买操作失败")
                
        except Exception as e:
            self.update_status(f"发生错误: {str(e)}")
            if driver:
                driver.quit()
                
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
                print(f"找到按钮，使用选择器: {selector}")
                break
            except:
                continue
                
        if ready_button:
            ready_button.click()
            print("已确认初始弹窗")
            # return True
        else:
            print("未找到弹窗按钮")
            # return False
            
        # 处理 Cookie 设置
        try:
            accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='btn-accept-all']"))
            )
            accept_button.click()
            print("已接受Cookie设置")
            time.sleep(1)
        except:
            print("没有找到Cookie设置按钮，继续执行")

        return True
    except Exception as e:
        print(f"处理初始弹窗时发生错误: {e}")
        return False

def wait_for_wallet_connection(driver):
    """等待用户连接钱包并确认连接成功"""
    try:
        # 等待连接钱包按钮出现并可点击
        connect_button = WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/nav/div[2]/button"))
        )
        print("请连接钱包...")
        
        # 等待钱包连接成功（通过检查 view profile 文字是否出现）
        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'view profile')]"))
        )
        print("钱包连接成功！")
        return True
    except Exception as e:
        print(f"等待钱包连接超时或发生错误: {e}")
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
            print("已选择代币")
            return True
        except Exception as e:
            print(f"未找到搜索结果: {e}")
            # 尝试备用选择器
            try:
                first_result = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//main//div[contains(@class, 'overflow-hidden')]//a[1]/div"))
                )
                first_result.click()
                print("使用备用选择器选择代币成功")
                return True
            except:
                print("备用选择器也未找到结果")
                return False
            
    except Exception as e:
        print(f"搜索代币时发生错误: {e}")
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
            EC.presence_of_element_located((By.XPATH, "//input[@type='number']"))
        )
        sol_input.clear()  # 清除默认值
        sol_input.send_keys(str(sol_amount))  # 输入SOL数量
        time.sleep(1)  # 等待输入完成
        
        # 等待并点击购买按钮
        buy_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buy')]"))
        )
        buy_button.click()
        
        print("已发起购买交易")
        return True
    except Exception as e:
        print(f"购买过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    app = PumpAutoBuyApp()
    app.run()

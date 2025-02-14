import os
import sys
import time
from os import device_encoding

from selenium.webdriver.support import expected_conditions as EC

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def openChrome(url):
    # 设置 Chrome 的选项（例如，无头模式、禁用 GPU 等）
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless")  # 无头模式（可选）开启时浏览器没有打开
    # chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速（可选）
    # chrome_driver_path = "/Users/chenk/Downloads/chromedriver-mac-x64/chromedriver"
    # chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:52734")  # 设置远程调试地址
    # 使用 Service 来指定 ChromeDriver 路径
    # service = Service(executable_path=chrome_driver_path)
    # driver = webdriver.Chrome(service=service, options=chrome_options)

    # 使用 WebDriverManager 自动下载和管理 chromedriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    # 打开网页
    driver.get(url)
    return driver

def show_help():
    print("""
    可用指令：
    1. start index   - 启动程序 从第几个开始
    2. help          - 显示帮助信息
    3. exit          - 退出程序
    """)


def delete_lines_and_get_data(file_path, num_lines_to_delete):
    # 用于存储删除的行数据
    deleted_lines = []

    # 创建一个临时文件路径
    temp_file_path = file_path + ".temp"

    # 打开原始文件和临时文件
    with open(file_path, 'r') as file, open(temp_file_path, 'w') as temp_file:
        line_count = 0  # 计数读取的行数

        # 逐行读取文件
        for line in file:
            # 如果读取的行数小于需要删除的行数，则将这些行存入 deleted_lines
            if line_count < num_lines_to_delete:
                deleted_lines.append(line.strip())  # 删除的行数据存入数组
                line_count += 1  # 增加已删除行的计数
            else:
                temp_file.write(line)  # 将未删除的行写入临时文件

    # 删除原文件，并重命名临时文件为原文件
    os.remove(file_path)  # 删除原文件
    os.rename(temp_file_path, file_path)  # 用临时文件替换原文件

    return deleted_lines

def select_sol_and_set_addr(driver, addr, index):
    # 选择输入框
    select_input_xpath = f'//*[@id="pane-addAddress"]/div/div[2]/div[{index + 1}]/div[2]/div/div[1]/input'
    # 地址输入框
    addr_input_str = f'//*[@id="pane-addAddress"]/div/div[2]/div[{index + 1}]/div[6]/div/input'
    # 选择 SOL
    sol_position_xpath = f'/html/body/div[{index+7}]/div[1]/div[1]/ul/div/div[1]/div[1]/li/div/div/span'

    if index == 0:
        select_input_xpath = '''//*[@id="pane-addAddress"]/div/div[2]/div/div[2]/div/div[1]/input'''
        addr_input_str = '//*[@id="pane-addAddress"]/div/div[2]/div/div[6]/div/input'
        sol_position_xpath = '/html/body/div[7]/div[1]/div[1]/ul/div/div[1]/div[1]/li/div/div/span'

    try:
        if index == 0:
            select_input = driver.find_element(By.XPATH, select_input_xpath)
            select_input.click()
            time.sleep(0.5)
            select_input.send_keys("SOL")  # 使用 send_keys 来填充输入框的值
            time.sleep(1)
            sol = driver.find_element(By.XPATH, sol_position_xpath)
            sol.click()
            time.sleep(0.5)

        addr_input = driver.find_element(By.XPATH, addr_input_str)
        addr_input.send_keys(addr)
        time.sleep(0.5)

    except Exception as e:
        print(f"界面不对: {e}")
        return False

    return True

def read_lines_from_file(file_path, start_line, num_lines):
    """
    从文件中读取从 start_line 开始的 num_lines 行数据。

    :param file_path: 文本文件路径
    :param start_line: 起始行号（从1开始）
    :param num_lines: 要读取的行数
    :return: 返回读取的行数据列表
    """
    lines = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for current_line, content in enumerate(file, start=1):
                if current_line >= start_line:
                    lines.append(content.strip())
                if len(lines) == num_lines:
                    break
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
    except Exception as e:
        print(f"发生错误: {e}")
    return lines

def run(start_index):
    print("running")
    # 获取打包后的可执行文件所在目录
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)  # 获取打包后的可执行文件目录
    else:
        base_path = os.path.abspath(".")  # 开发环境中的当前目录

    # 构建 addr.txt 的完整路径
    addr_path = os.path.join(base_path, "addr.txt")
    addrs = read_lines_from_file(addr_path,  start_index, 50)
    index = 0
    for addr in addrs:
        if index > 0:
            add.click()

        print(f"第 {start_index+index} 个 addr => ", addr)
        try:
            result = select_sol_and_set_addr(driver, addr, index)
            if not result:
                break
            add = driver.find_element(By.XPATH, '//*[@id="pane-addAddress"]/div/div[3]/div[1]/div')
        except Exception as e:
            print("找不到元素, 请确定界面是否正确")

        index = index + 1

def waitForCmd():
    while True:
        # 提示用户输入指令
        command = input("请输入指令 (输入 'help' 获取指令列表): ").strip().lower()
        if command.startswith("start"):
            # 尝试提取数字
            parts = command.split()
            if len(parts) == 2 and parts[1].isdigit():
                index = int(parts[1])
                run(index)
                print("此次操作完毕")
            else:
                print("无效的 start 指令，请输入 'start [数字]'")
        elif command == "help":
            show_help()
        elif command == "exit":
            print("退出程序...")
            break
        else:
            print("无效指令，请重新输入。")

if __name__ == "__main__":
    # 看版本 chrome://settings/help
    # https://www.bitget.com/asset/addressBook
    driver = openChrome("https://www.bitget.com/asset/batchAdd?batchType=1")
    waitForCmd()
    # driver.quit()




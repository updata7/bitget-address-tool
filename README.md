# bitget-address-tool

## bitget 批量添加地址工具

- 运行环境 macOS，双击 main 即开始运行
- 地址存放路径：同目录下 addr.txt，一行一个，每次最多读50个，已读取的会删掉，未读取的仍保留
- 在工具打开的浏览器里，登录bitget账号，并打开到这个界面: https://www.bitget.com/asset/batchAdd?batchType=1
- 在终端输入 start 并回车，当 addr.txt 里有数据的时候，会自动输入



### 打包指令
pyinstaller --onefile main.py

pyinstaller --name="PumpAutoBuy" --windowed --clean pump_auto_buy.py

### 推荐
这个程序在 Windows 10 和 Windows 11 上运行最佳，原因如下：
Chrome WebDriver 支持：
Windows 10/11 对最新版本的 Chrome 和 WebDriver 支持最好
自动化驱动程序安装和更新更稳定
Python 环境：
Windows 10/11 对 Python 3.x 支持良好
pip 包管理和依赖安装更可靠
DPI 缩放：
Windows 10/11 提供了更好的高 DPI 显示支持
GUI 界面在高分辨率屏幕上显示更清晰
系统权限：
Windows 10/11 的权限管理更完善
配置文件的读写更安全
兼容性建议：
建议使用 Windows 10 21H2 或更高版本
Windows 11 任何版本都可以
需要安装 Chrome 浏览器（最新版本即可）
建议使用管理员权限运行程序，以确保配置文件可以正常保存
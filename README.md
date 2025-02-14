# bitget-address-tool

## bitget 批量添加地址工具

- 运行环境 macOS，双击 main 即开始运行
- 地址存放路径：同目录下 addr.txt，一行一个，每次最多读50个，已读取的会删掉，未读取的仍保留
- 在工具打开的浏览器里，登录bitget账号，并打开到这个界面: https://www.bitget.com/asset/batchAdd?batchType=1
- 在终端输入 start 并回车，当 addr.txt 里有数据的时候，会自动输入



### 打包指令
pyinstaller --onefile main.py
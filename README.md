# 使用 Python 对明御堡垒机后的服务器进行自动化运维

明御®运维审计与风险控制系统（堡垒机）[1] 是由安恒信息出品的堡垒机产品，其支持通过 Web 界面与 SSH 对主机进行运维 [2]。

其 Web 界面提供了批量运维的功能，用户可以通过申请 “API 访问键” 实现自动化运维；

而在其 SSH 方式中，运维者首先需要通过 SSH 协议登陆到统一的堡垒机，登陆后将会得到一个交互式终端，该终端无法执行系统命令，仅有选择服务器等基础功能。运维者需要通过方向键选择要运维的服务器，敲回车后，将会由该堡垒机连接内网的服务器，界面将会变为内网服务器的终端，此时将与直连内网服务器进行操作没有区别。

本项目通过使用 Paramiko 库将上述 SSH 方式的认证过程进行了自动化。通过使用本项目，你可以使用 Python 对明御堡垒机后的服务器进行自动化运维（批量执行 Shell 命令、批量获取交互式终端等），可以方便地与其他系统进行集成。

注意：堡垒机有能力“录制”你与堡垒机的完整交互过程，用于后续的安全审计。

## 环境搭建

```bash
# 安装 Python, pip, Poetry
sudo apt install python3 python3-pip
python3 -m pip install --upgrade pip
python3 -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python3 -m pip install poetry

# 下载代码
git clone https://github.com/WangYihang/DBAPPSecurity-Unified-Security-Management-Python-Connector
cd DBAPPSecurity-Unified-Security-Management-Python-Connector
poetry install
```

## 运行

1. 将 `example.secrets.toml` 复制为 `.secrets.toml`；
2. 编辑 `.secrets.toml`，填入对应的认证信息；
    1. `DAMDDOS_ENDPOINT` 堡垒机地址，如：`sso.example.com:60022`；
    2. `DAMDDOS_USERNAME` 堡垒机账号；
    3. `DAMDDOS_PASSWORD` 堡垒机密码；
    4. `DAMDDOS_OTP_SECRET` 堡垒机“手机身份验证器”的“密钥”；
3. 运行自动化运维脚本

    ```
    poetry run python main.py
    ```

## FAQ

1. 如何获取身份验证码

    ```
    poetry run python -c 'import pyotp; from config import settings; print(pyotp.TOTP(settings.DAMDDOS_OTP_SECRET).now())'
    ```

2. 可否通过 Paramiko 向内网服务器上传/下载文件？

    不能（应该）。

[1]: https://www.dbappsecurity.com.cn/product/cloud157.html
[2]: https://netmarket.oss.aliyuncs.com/9197aa5f-6fc2-47bd-8d35-f6b3c8e09b18.pdf
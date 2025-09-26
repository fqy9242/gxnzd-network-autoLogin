import http.client
import urllib.parse
import time
import sys
import json
import socket


OPERATOR_CHOICE = 3
ACCOUNT = ""
PASSWORD = ""


OPERATOR_MAP = {
    1: {"name": "中国移动", "suffix": "@cmcc"},
    2: {"name": "中国电信", "suffix": "@telecom"},
    3: {"name": "中国联通", "suffix": "@unicom"},
    4: {"name": "校园用户", "suffix": "@campus"}
}
V_PARAM = "6045"
PORTAL_HOST = "http://10.10.10.2"
CHECK_INTERVAL_SECONDS = 300 # 重试间隔

def get_local_ip():

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('114.114.114.114', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 错误：无法获取本机IP地址 - {e}")
        return None

def check_or_login(operator_config):

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    local_ip = get_local_ip()
    if not local_ip:
        print(f"[{timestamp}] 跳过：因无法获取IP地址。")
        return

    full_username = f"{ACCOUNT}{operator_config['suffix']}"
    print(f"[{timestamp}] 正在查询/登录账号: {full_username}...")
    
    try:
        params = {'callback': 'dr1003', 'login_method': '1', 'user_account': full_username, 'user_password': PASSWORD, 'wlan_user_ip': local_ip, 'v': V_PARAM}
        query_string = urllib.parse.urlencode(params)
        path = f"/eportal/portal/login?{query_string}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0', 'Host': f'{PORTAL_HOST.split("//")[1]}:801'}
        
        conn = http.client.HTTPConnection(PORTAL_HOST.split("//")[1], 801, timeout=10)
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
    except Exception as e:
        print(f"[{timestamp}] 错误：请求过程中发生错误 - {e}")
        return

    if res.status != 200:
        print(f"[{timestamp}] 错误：服务器响应异常 (HTTP Code: {res.status} {res.reason})。")
        return
        
    try:
        response_text = data.decode("utf-8")
    except UnicodeDecodeError:
        response_text = data.decode("gb2312", errors='ignore')
    
    if not response_text.startswith('dr1003('):
        print(f"[{timestamp}] 警告：收到意外的响应格式。")
        return
    
    try:
        clean_response = response_text.strip().rstrip(';')
        json_str = clean_response[len('dr1003('):-1]
        json_data = json.loads(json_str)
        
        result = json_data.get('result')
        msg = json_data.get('msg', '')

        if str(result) == '1':
            status = f"状态：登录成功！ ({msg})"
        elif '已经在线' in msg:
            status = f"状态：已在线，无需操作。 ({msg})"
        else:
            status = f"警告：认证失败 -> {msg}"
        print(f"[{timestamp}] {status}")

    except (json.JSONDecodeError, IndexError) as e:
        print(f"[{timestamp}] 错误：解析服务器JSON响应时出错 - {e}。 响应(部分): {response_text[:100]}")


if __name__ == "__main__":
    if OPERATOR_CHOICE not in OPERATOR_MAP:
        print(f"错误：无效的运营商选择 '{OPERATOR_CHOICE}'。请在脚本顶部设置为 1, 2, 3, 或 4。")
        sys.exit(1)

    selected_operator = OPERATOR_MAP[OPERATOR_CHOICE]

    print(f"当前选择: [{selected_operator['name']}] - 账户: {ACCOUNT}")
    
    check_or_login(selected_operator)
    
    while True:
        try:
            time.sleep(CHECK_INTERVAL_SECONDS)
            check_or_login(selected_operator)
        except KeyboardInterrupt:
            print("\n程序已手动退出。")
            sys.exit(0)
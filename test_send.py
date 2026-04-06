import requests

BASE = "http://127.0.0.1:3000"

# 如果你在 OneBot11 配置里设置了 access_token，填这里；没设置就留空字符串
ACCESS_TOKEN = "vG6gx8QYG6TU7bfu"

def call_api(action: str, params: dict):
    url = f"{BASE}/{action}"

    headers = {}
    if ACCESS_TOKEN:
        # 常见带法：Bearer
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"

        # 如果你遇到 401/403，可以把上一行改成下面这种再试：
        # headers["Authorization"] = ACCESS_TOKEN

        # 或改成 URL 参数（某些实现吃这个）：
        # url = f"{BASE}/{action}?access_token={ACCESS_TOKEN}"

    r = requests.post(url, json=params, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def send_private_msg(user_id: int, message: str):
    return call_api("send_private_msg", {"user_id": user_id, "message": message})

if __name__ == "__main__":
    # 先确认接口仍通
    print(call_api("get_status", {}))

    # 发私聊（把 目标QQ号 换成你要发的人）
    target =  2997146528
    resp = send_private_msg(target, "测试：NapCat OneBot11 发消息成功了吗？")
    print(resp)



from src.updatenews.fetch import default_daily_window, get_matches_in_window
from src.updatenews.storage import load_receivers, load_onebot_config
from src.updatenews.notifier import (
    OneBot11Client,
    OneBot11Config,
    format_daily_report,
    send_report_to_receivers,
)

def run_once():
    start, end = default_daily_window()
    matches = get_matches_in_window(start, end)
    text = format_daily_report(matches, start, end)

    receivers = load_receivers("receivers.json")

    base_url, token = load_onebot_config("onebot_config.json")
    if not base_url or not token:
        raise SystemExit(
            "onebot_config.json 未配置完整：请填写 base_url 和 token 后再运行。"
        )

    client = OneBot11Client(OneBot11Config(base_url=base_url, token=token))

    results = send_report_to_receivers(client, receivers, text)
    print(results)

if __name__ == "__main__":
    run_once()

'''
ctrip_spider1:携程评论爬虫第2个进程，景点详情页爬取
读取 ctrip_spider0 生成的 {城市}_携程景点.csv，批量获取详情页 URL。
'''
import csv
import os
import time
import requests
import json
import random
from fake_useragent import UserAgent
from urllib.parse import quote
from ctrip_spider0 import get_spot


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
]

def random_headers(keyword):
    """动态构造headers"""
    return {
        'authority': 'm.ctrip.com',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type': 'application/json',
        'cookieorigin': 'https://you.ctrip.com',
        'origin': 'https://you.ctrip.com',
        'priority': 'u=1, i',
        'referer': f'https://you.ctrip.com/globalsearch/?keyword={requests.utils.quote(keyword)}',
        'user-agent': random.choice(USER_AGENTS),
    }

def safe_post(url, params, cookies, json_data, keyword, max_retries=5):
    """带重试机制的 POST 请求"""
    for attempt in range(1, max_retries + 1):
        try:
            headers = random_headers(keyword)
            resp = requests.post(
                url, params=params, headers=headers,
                cookies=cookies, json=json_data, timeout=30
            )
            if resp.status_code == 200:
                return resp
            else:
                print(f"状态码 {resp.status_code}，重试 {attempt}/{max_retries}")
        except requests.exceptions.RequestException as e:
            print(f"请求失败({attempt}/{max_retries}): {e}")

        sleep_time = random.uniform(4, 10)
        print(f"⏳ 等待 {sleep_time:.1f}s 后重试...")
        time.sleep(sleep_time)

    print("达到最大重试次数，放弃该请求。")
    return None

def extract_sight_id_from_url(url):
    """从URL中提取sight/后的内容"""
    if not url:
        return ""

    sight_index = url.find("sight/")
    if sight_index == -1:
        return ""

    start_index = sight_index + 6
    end_index = url.find(".html", start_index)

    if end_index == -1:
        return url[start_index:]
    else:
        return url[start_index:end_index]


def calculate_match_score(search_term, result_name):
    """
    计算搜索词和结果名称的匹配度
    返回0-1之间的分数，越高表示匹配度越好
    """
    import difflib
    from fuzzywuzzy import fuzz  # 需要安装: pip install fuzzywuzzy python-Levenshtein

    search_term = search_term.lower().strip()
    result_name = result_name.lower().strip()

    # 如果完全一致，直接返回最高分
    if search_term == result_name:
        return 1.0

    # 方法1: 使用fuzzywuzzy的partial_ratio（部分匹配）
    partial_ratio = fuzz.partial_ratio(search_term, result_name) / 100.0

    # 方法2: 使用difflib的序列匹配
    sequence_ratio = difflib.SequenceMatcher(None, search_term, result_name).ratio()

    # 方法3: 检查是否包含关键词
    search_words = set(search_term.replace('，', ' ').replace(',', ' ').split())
    result_words = set(result_name.replace('，', ' ').replace(',', ' ').split())

    keyword_overlap = len(search_words & result_words) / len(search_words) if search_words else 0

    # 综合评分（加权平均）
    final_score = (partial_ratio * 0.5 + sequence_ratio * 0.3 + keyword_overlap * 0.2)

    return final_score


def clean_search_term(term):
    """
    清理搜索词，移除可能干扰搜索的字符
    """
    import re
    # 移除括号及括号内的内容
    # term = re.sub(r'[\(（].*?[\)）]', '', term)
    # 移除特殊字符
    term = re.sub(r'[^\w\u4e00-\u9fff\(\)（）]', '', term)
    # 合并多个空格
    term = re.sub(r'\s+', ' ', term).strip()
    return term


def search_with_city_name(scenic_spot, city):
    """
    分步搜索策略：
    1. 先尝试纯景点名
    2. 如果失败，尝试添加城市名
    """
    # 第一步：纯景点名搜索
    print(f"第一步搜索: '{scenic_spot}'")
    result = get_scenic_spot_data(scenic_spot)

    if result and result.get("detail_url"):
        return result

    # 第二步：景点名 + 城市名搜索
    print(f"第一步失败，尝试: '{scenic_spot}, {city}'")
    combined_search = f"{scenic_spot}, {city}"
    time.sleep(random.uniform(2, 4))  # 等待一下再尝试
    result = get_scenic_spot_data(combined_search)

    if result and result.get("detail_url"):
        # 检查结果是否在目标城市
        district = result.get("district_name", "")
        if city in district or district in city:
            return result
        else:
            print(f"找到结果但不在目标城市 '{city}'，在 '{district}'")

    return None

def get_scenic_spot_data(scenicspot):
    """获取景点详情页信息"""

    # 基础URL
    url = "https://m.ctrip.com/restapi/soa2/20591/getGsOnlineResult"

    # 动态生成参数
    timestamp = int(time.time() * 1000)
    guid = ''.join(str(random.randint(0, 9)) for _ in range(20))
    x_trace_id = f"{guid}-{timestamp}-{random.randint(1000000, 9999999)}"

    params = {
        '_fxpcqlniredt': guid,
        'x-traceID': x_trace_id
    }

    headers = {
        'authority': 'm.ctrip.com',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type': 'application/json',
        'cookieorigin': 'https://you.ctrip.com',
        'origin': 'https://you.ctrip.com',
        'priority': 'u=1, i',
        'referer': f'https://you.ctrip.com/globalsearch/?keyword={requests.utils.quote(scenicspot)}',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': UserAgent().chrome
    }

    cookies = {
        'GUID': guid,
        'nfes_isSupportWebP': '1',
        '_RGUID': f'{guid[:8]}-{guid[8:12]}-{guid[12:16]}-{guid[16:20]}-{guid[20:32]}',
        '_bfaStatus': 'success',
    }

    json_data = {
        'head': {
            'auth': '',
            'cid': guid,
            'ctok': '',
            'cver': '1.0',
            'extension': [],
            'lang': '01',
            'sid': '8888',
            'syscode': '09',
            'xsid': '',
        },
        'keyword': scenicspot,
        'pageIndex': 0,
        'pageSize': 12,
        'profile': False,
        'sourceFrom': '',
        'tab': 'sight',
    }

    try:
        # 添加随机延迟
        time.sleep(random.uniform(3, 8))
        response = safe_post(url, params, cookies, json_data, scenicspot)
        if response is None:
            print(f"请求 {scenicspot} 失败（多次重试仍无响应）")
            return None

        if response.status_code == 200:
            data = response.json()
            # print(f"响应状态: {data.get('ResponseStatus', {}).get('Ack')}")

            # 检查API响应状态
            if data.get("ResponseStatus", {}).get("Ack") == "Success":
                # 提取items列表
                items = data.get("items", [])

                # 过滤出景点类型的数据
                sight_items = [item for item in items if item.get("type") == "sight"]

                for item in items:
                    t = item.get("type", "")
                    name = item.get("word", "")
                    if t == "sight" and not any(
                            kw in name for kw in ["演唱会", "音乐节", "嘉年华", "Live", "话剧", "演出", "巡演", "舞剧", "舞台剧", "歌剧", "音乐剧"]
                    ):
                        sight_items.append(item)

                if not sight_items:
                    print(f"未找到 '{scenicspot}' 对应的景点（可能是活动或演出类结果）")
                    return None

                # first_item = sight_items[0]# 只取第一个景点

                # 搜索结果验证和评分
                scored_items = []
                for item in sight_items:
                    item_name = item.get("word", "")
                    score = calculate_match_score(scenicspot, item_name)
                    scored_items.append((score, item))

                # 按匹配分数排序，选择最匹配的结果
                scored_items.sort(key=lambda x: x[0], reverse=True)
                best_match = scored_items[0]

                match_score, first_item = best_match
                item_name = first_item.get("word", "")

                print(f"搜索词: '{scenicspot}' → 匹配结果: '{item_name}' (匹配度: {match_score:.2f})")

                # 如果匹配度太低，认为搜索失败
                if match_score < 0.3:
                    print(f"匹配度过低，可能不是正确结果，跳过")
                    return None


                # 提取需要的数据
                district_name = first_item.get("districtName", "")
                detail_url = first_item.get("url", "")
                id = extract_sight_id_from_url(detail_url)
                encoded_city = quote(district_name, encoding='utf-8')
                detail_url = "https://you.ctrip.com/sight/"+ encoded_city + id +".html"
                sight_id = id.strip("/").split("/")[-1]
                sight_name = first_item.get("word", "")
                # print(f"  地区: {district_name}")
                # print(f"  Sight ID: {sight_id}")
                # print(f"  名称: {sight_name}")
                # print(f"  URL: {detail_url}")

                result = {
                    "district_name": district_name,
                    "sight_id": sight_id,
                    "sight_name": sight_name,
                    "detail_url": detail_url,
                }

                return result
            else:
                print("API返回失败状态")
                print(f"完整响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                return None
        else:
            print(f"HTTP状态码异常: {response.status_code}")
            print(f"响应文本: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        if 'response' in locals():
            print(f"响应内容: {response.text}")
        return None
    except Exception as e:
        print(f"获取景点 '{scenicspot}' 时异常: {e}")
        return None


def get_url(city):
    """
    主函数：读取 {city}_携程景点.csv，批量获取详情页链接
    :return: detail_urls
    """
    csv_file = f"{city}_携程景点.csv"
    temp_file = f"{city}_携程景点_tmp.csv"

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)  # 将reader转换为列表，后面统一使用 rows
            if not rows:
                print(f"文件 {csv_file} 为空")
                return [], []
            fieldnames = list(rows[0].keys())  # 从第一行获取字段名
    except FileNotFoundError:
        print(f"错误: 未找到文件 {csv_file}，请先运行 ctrip_spider0.py")
        return [], []
    except Exception as e:
        print(f"读取 {csv_file} 时出错: {e}")
        return [], []

    # 确保存在 "详情页URL" 列
    if "详情页URL" not in fieldnames:
        fieldnames.append("详情页URL")
        # 若 rows 中的每一行都缺少该键，先补空值，避免后续 KeyError
        for r in rows:
            if "详情页URL" not in r:
                r["详情页URL"] = ""

    # 统计初始状态
    initial_success = sum(1 for row in rows if row.get("详情页URL") and row["详情页URL"].strip())
    total_rows = len(rows)
    rows_to_process = total_rows - initial_success

    if rows_to_process == 0:
        print(f"总景点数: {total_rows}")
        print("所有景点的详情页URL已获取，无需重新爬取")
        return [], []
    else:
        print(f"总景点数: {total_rows}")
        print(f"已成功爬取: {initial_success} 个")
        print(f"待爬取: {rows_to_process} 个\n")

    detail_urls = []  # 存储所有详情页URL

    processed_count = 0
    success_count = 0

    # 遍历 rows（而不是已经耗尽的 reader）
    for i, row in enumerate(rows, 1):
        spot = row.get("景点", "")
        if not spot:
            continue

        # 如果该行已存在URL，则使用并跳过请求（断点续爬）
        if row.get("详情页URL"):
            detail_urls.append(row["详情页URL"])
            continue

        # print(f"[{i}/{len(rows)}] 正在搜索: {spot}")
        print(f"\n[{processed_count + 1}/{rows_to_process}] 正在处理: {spot}")

        # 清理搜索词
        cleaned_spot = clean_search_term(spot)
        if cleaned_spot != spot:
            print(f"清理搜索词: '{spot}' → '{cleaned_spot}'")

        # 获取景点信息
        # # 获取第一个景点信息
        # spot_info = get_scenic_spot_data(spot)

        # spot_info = get_scenic_spot_data(cleaned_spot)
        # 使用改进的搜索策略
        spot_info = search_with_city_name(cleaned_spot, city)


        if spot_info and spot_info.get("detail_url"):
            url = spot_info["detail_url"]
            row["详情页URL"] = url
            detail_urls.append(url)
            success_count += 1
            print(f"成功: {spot_info['sight_name']} → {url}")
        else:
            row["详情页URL"] = ""
            detail_urls.append(None)
            print(f"✗ 未找到 {spot} 的详情页")

        processed_count += 1

        # # 每采集一条就写入临时文件（防断点）
        # with open(temp_file, 'w', encoding='utf-8-sig', newline='') as f:
        #     writer = csv.DictWriter(f, fieldnames=fieldnames)
        #     writer.writeheader()
        #     writer.writerows(rows)

        # 关键修改：直接保存到原始文件（实现真正的断点续爬）
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # 随机延迟，避免被封
        if processed_count < rows_to_process:  # 最后一条不需要延迟
            delay = random.uniform(3, 6)
            if processed_count % 20 == 0:
                delay = random.uniform(10, 20)
                current_success = initial_success + success_count
                print(f"进度: {current_success}/{total_rows} (本次新增: {success_count})")
                print(f"防止被封，休息 {delay:.1f}秒...")
            time.sleep(delay)

        # # 统计成功数量
        # if i % 10 == 0 or i == len(rows):
        #     print(f"—— 已成功补充 {success_count}/{i} 条景点详情页 ——\n")

    # os.replace(temp_file, csv_file)
    print(f"\n===============================")
    print(f"\n===========处理完成!============")
    print(f"总共处理: {processed_count} 条")
    print(f"新增成功: {success_count} 条")
    print(f"最终成功: {initial_success + success_count}/{total_rows}")
    print(f"文件已更新: {csv_file}\n")
    return detail_urls


'''
问题:
1.每次调用 UserAgent().chrome 其实生成速度慢且容易重复。
没有随机 UA 池。
没有重试机制。
延时太短。

2.寻找的景点有些好像不在北京(确定了)
冰心故居
响应状态: Success
成功: 三坊七巷, 福州 → https://you.ctrip.com/sight/%E7%A6%8F%E5%B7%9E164/64505.html

3.寻找url时有些结果和原景点和完全不同

以上已解决(改用原始方法。直接调用接口)

4.可能没有设置补漏措施，再重新运行代码时需要跳过已成功获取url的
待解决:已新增补漏代码，但是仍旧存在无法搜索到的景点，稍后将进行手动检查
'''
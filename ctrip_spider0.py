'''
ctrip_spider0:携程评论爬虫第1个进程
负责获取需要爬取的景点名

按照初定想法，爬取单个城市的所有景点
'''
import csv
import os
import time
import requests
import json
import random
from fake_useragent import UserAgent
from urllib.parse import quote

def get_spots_name(city, max_pages=300, cityId=1):
    """获取城市里所有景点名的函数"""

    page = 1
    all_spots = []  # 存储所有景点信息
    retry_count = 0  # 连续失败计数

    # 定义需要过滤的非景点类型（统一小写，方便匹配）
    FILTER_TYPES = {
        '演唱会', '演出', '话剧', 'SPA/按摩', '脱口秀',
        'livehouse', '舞蹈舞剧', '音乐会'
    }

    # 保存文件名
    filename = f"{city}_携程景点.csv"

    # 若存在历史文件，加载进度
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = list(csv.DictReader(f))
            all_spots = reader
        print(f"检测到已有进度文件 {filename}，已采集 {len(all_spots)} 条数据，将继续采集...")
        page = len(all_spots) // 10 + 1  # 每页10条，估算下一页页码

    # 基础URL
    url = "https://m.ctrip.com/restapi/soa2/18109/json/getAttractionList"

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
        # 'referer': f'https://you.ctrip.com/sight/{quote(city)}{cityId}.html',
        'referer': 'https://m.ctrip.com',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99" ',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': UserAgent().edge,
        'x-ctx-ubt-pageid': '10650142842',  # 添加这些关键header
        'x-ctx-ubt-pvid': str(random.randint(1, 10)),
        'x-ctx-ubt-sid': str(random.randint(10, 20)),
        'x-ctx-ubt-vid': '1761562932386.4248f8KGlzH5',
        # 'x-ctx-wclient-req': '9e29e1d406c2493db1c2b329f4e09c0b'  # 这个可能是动态的，先注释
    }

    cookies = {
        'GUID': guid,
        '_RGUID': f'{guid[:8]}-{guid[8:12]}-{guid[12:16]}-{guid[16:20]}-{guid[20:32]}',
        ' nfes_isSupportWebP':'1',
        ' UBT_VID':'1761562932386.4248f8KGlzH5',
        ' MKT_CKID':'1761562932910.bh1sl.0c1x',
        ' _bfaStatusPVSend':'1',
        ' _ubtstatus':'%7B%22vid%22%3A%221761562932386.4248f8KGlzH5%22%2C%22sid%22%3A8%2C%22pvid%22%3A2%2C%22pid%22%3A600001375%7D',
        ' _bfaStatus':'send',
        ' _bfa':'1.1761562932386.4248f8KGlzH5.1.1762514025531.1762514065973.12.10.10650142842',
        ' _jzqco':'%7C%7C%7C%7C1762504676914%7C1.1184393495.1761562932912.1762514026211.1762514066757.1762514026211.1762514066757.undefined.0.0.118.118',
        # 'HMACCOUNT': '8B8F963FE4B73935',
        # 'MKT_Pagesource': 'PC',
    }

    # 若文件不存在，写入表头
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f,
                                    fieldnames=["景点", "具体位置", "总评分", "imageUrl", "景点类型", "热度", "等级"])
            writer.writeheader()

    while page <= max_pages:
        print(f"正在获取第{page}页景点数据...")
        time.sleep(random.uniform(3, 6))  # 每页间隔 3～6 秒

        json_data = {
            'filter': {
                'fileterItems': []
            },
            'head': {
                'auth': '',
                'cid': guid,
                'ctok': '',
                'cver': '1.0',
                'extension': [],
                'lang': '01',
                'sid': '8888',
                'syscode': '999',
                'xsid': '',
            },
            'index': page,
            'returnModuleType': 'product',
            'scene': 'online',
            'sortType': 1,
            'count': 10,
            'districtId': cityId,
        }

        try:
            # 使用会话保持
            session = requests.Session()

            # 打印调试信息
            print(f"请求URL: {url}")
            # print(f"请求参数: {params}")

            response = requests.post(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                json=json_data,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                print(f"响应状态: {data.get('ResponseStatus', {}).get('Ack')}")

                # 检查API响应状态
                if data.get("ResponseStatus", {}).get("Ack") == "Success":
                    # 提取attractionList列表
                    attractionlist = data.get("attractionList", [])

                    # 调试信息
                    print(f"attractionList 长度: {len(attractionlist)}")
                    # print(f"hasMore: {data.get('hasMore', False)}")

                    # 打印完整的响应结构以便分析
                    # print(f"响应中的所有键: {list(data.keys())}")

                    # 检查是否有其他可能包含景点数据的字段
                    for key in data.keys():
                        if key != "ResponseStatus" and isinstance(data[key], list) and len(data[key]) > 0:
                            print(f"发现列表字段 {key}: 长度={len(data[key])}")
                            # if len(data[key]) > 0 and isinstance(data[key][0], dict):
                            #     print(f"第一个元素: {data[key][0]}")

                    if not attractionlist:
                        print(f"第{page}页没有景点数据")
                        # 打印更多调试信息
                        print(f"完整响应: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}...")

                        # 检查是否是最后一页
                        if not data.get("hasMore", False):
                            print("没有更多数据，停止采集")
                            break
                        else:
                            print("有hasMore但attractionList为空，可能是API限制")
                            retry_count += 1
                            if retry_count >= 3:
                                print("连续3页无数据，停止采集")
                                break
                            page += 1
                            continue

                    spots_this_page = []
                    # 处理当前页的景点数据
                    for attraction in attractionlist:
                        card = attraction.get("card", {})
                        # print(card.keys())
                        tag_list = card.get("tagNameList", [])  # 获取原始标签列表
                        spot_type = ", ".join(tag_list)  # 多标签转字符串（比如["自然风光","人文古迹"]→"自然风光, 人文古迹"）
                        print(card.get("coverImageUrl", ""))

                        spot_info = {
                            "景点": card.get("poiName", "未知景点"),  # 景点名称
                            "具体位置": card.get("zoneName", ""),  # 区域名称
                            "总评分": card.get("commentScore", 0),  # 评分
                            "imageUrl": card.get("coverImageUrl", ""),  # 图片URL
                            "景点类型": spot_type,
                            "热度": card.get("heatScore", ""), #热度
                            "等级": card.get("sightLevelStr", ""), #星级/等级
                        }

                        # 1. 筛选判断（不转小写，直接精准匹配）
                        need_filter = False
                        # 条件1：过滤景点类型为空（含纯空格）
                        if not spot_type.strip():
                            need_filter = True
                        # 过滤包含任意指定非景点类型（精准大小写匹配）
                        else:
                            for filter_type in FILTER_TYPES:
                                # 直接用原始字符串判断，不转lower()
                                if filter_type in spot_type:
                                    need_filter = True
                                    break
                            # 3. 仅保留非过滤数据
                            if not need_filter:
                                spots_this_page.append(spot_info)
                                all_spots.append(spot_info)
                            else:
                                print(f"过滤非景点数据：{spot_info['景点']}（类型：{spot_type}）")
                        # spots_this_page.append(spot_info)
                        # all_spots.append(spot_info)

                    # 写入文件
                    with open(filename, 'a', encoding='utf-8-sig', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=spots_this_page[0].keys())
                        writer.writerows(spots_this_page)

                    print(f"第{page}页采集完毕，本页共采集 {len(attractionlist)} 条景点")

                    # 成功后重置重试计数
                    retry_count = 0

                    # 检查是否还有更多数据
                    has_more = data.get("hasMore", False)
                    if not has_more:
                        print("已获取所有景点数据")
                        break

                    page += 1

                else:
                    error_msg = data.get("ResponseStatus", {}).get("Errors", [{}])[0].get("Message", "未知错误")
                    print(f"第{page}页请求失败: {error_msg}")
                    # 打印完整错误信息
                    print(f"完整错误响应: {json.dumps(data, ensure_ascii=False)[:500]}...")

                    retry_count += 1
                    if retry_count > 3:
                        print("连续失败3次，停止采集")
                        break
                    continue

            else:
                print(f"第{page}页HTTP请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                retry_count += 1
                if retry_count > 3:
                    print("连续失败3次，停止采集")
                    break
                continue

        except Exception as e:
            print(f"第{page}页请求异常: {str(e)}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            retry_count += 1

            if retry_count <= 3:
                wait_time = random.randint(120, 300)
                print(f"休眠 {wait_time} 秒后重试（第{retry_count}次）...")
                time.sleep(wait_time)
                continue
            else:
                print("连续3次失败，保存进度并结束采集。")
                break

    print(f"\n全部采集完成，共采集 {len(all_spots)} 条景点")
    return all_spots


def get_spots_by_search(city, max_pages=20):
    """通过搜索API获取景点列表 - 备用方案"""

    filename = f"{city}_携程景点.csv"
    all_spots = []

    # 基础URL - 使用搜索API
    url = "https://m.ctrip.com/restapi/soa2/20591/getGsOnlineResult"

    print(f"使用搜索API获取 {city} 的景点数据...")

    for page in range(max_pages):
        print(f"正在获取第{page + 1}页数据...")

        guid = ''.join(str(random.randint(0, 9)) for _ in range(20))
        timestamp = int(time.time() * 1000)
        x_trace_id = f"{guid}-{timestamp}-{random.randint(1000000, 9999999)}"

        params = {
            '_fxpcqlniredt': guid,
            'x-traceID': x_trace_id
        }

        headers = {
            'authority': 'm.ctrip.com',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'https://you.ctrip.com',
            'referer': f'https://you.ctrip.com/globalsearch/?keyword={quote(city)}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        }

        cookies = {
            'GUID': guid,
            '_RGUID': f'{guid[:8]}-{guid[8:12]}-{guid[12:16]}-{guid[16:20]}-{guid[20:32]}',
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
                'syscode': '999',
                'xsid': '',
            },
            'keyword': f"{city}景点",
            'pageIndex': page,
            'pageSize': 12,
            'profile': False,
            'sourceFrom': '',
            'tab': 'sight',
        }

        try:
            session = requests.Session()
            response = session.post(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                json=json_data,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ResponseStatus", {}).get("Ack") == "Success":
                    items = data.get("items", [])
                    sight_items = [item for item in items if item.get("type") == "sight"]

                    print(f"找到 {len(sight_items)} 个景点")

                    if not sight_items:
                        print("没有更多景点数据")
                        break

                    for item in sight_items:
                        spot_info = {
                            "景点": item.get("word", "未知景点"),
                            "具体位置": item.get("districtName", ""),
                            "总评分": item.get("commentScore", 0),
                            "imageUrl": item.get("imageUrl", ""),
                            "景点类型": ", ".join(item.get("tagNameList", [])),  # 列表转字符串
                            "热度": item.get( "heatScore", ""), #热度
                            "等级": item.get("sightLevelStr", ""), #星级/等级
                        }
                        all_spots.append(spot_info)

                    # 写入文件
                    with open(filename, 'a', encoding='utf-8-sig', newline='') as f:
                        if page == 0 and not os.path.exists(filename):
                            writer = csv.DictWriter(f, fieldnames=spot_info.keys())
                            writer.writeheader()
                        writer = csv.DictWriter(f, fieldnames=spot_info.keys())
                        writer.writerows([spot_info for spot_info in all_spots[len(all_spots) - len(sight_items):]])

                    time.sleep(random.uniform(2, 4))

            else:
                print(f"请求失败: {response.status_code}")

        except Exception as e:
            print(f"请求异常: {e}")

        time.sleep(random.uniform(3, 6))

    print(f"搜索完成，共获取 {len(all_spots)} 个景点")
    return all_spots

def save_spots_to_file(spots, city):
    """将景点数据保存到文件"""
    filename= f"{city}_携程景点.csv"

    # 定义CSV文件的列头
    fieldnames = ["景点", "具体位置", "总评分", "imageUrl", "景点类型", "热度", "等级"]   # "imageUrl",
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        # 写入列头
        writer.writeheader()

        # 写入每个景点的数据
        for spot in spots:
            writer.writerow(spot)

    print(f"已保存{len(spots)}个景点数据到 {filename}")


def find_city_id(city_name):
    """
    从cities.csv文件中查找城市ID（逗号分隔版本）
    :param city_name: 城市名称
    :return: 城市ID，如果未找到则返回None
    """
    csv_file = "cities.csv"

    if not os.path.exists(csv_file):
        print(f"错误: 未找到 {csv_file} 文件")
        return None

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)  # 默认使用逗号分隔

            for row in reader:
                if row['城市名称'] == city_name:
                    return int(row['城市ID'])

        print(f"在{csv_file}中未找到城市 '{city_name}'")
        return None

    except Exception as e:
        print(f"读取{csv_file}文件时出错: {e}")
        return None

def get_spot():
    '''
    :return: spots景点名列表
    '''
    print("请输入要爬取景区信息的城市名称:")
    city = input().strip()

    print("寻找城市id中...")
    # 从cities.csv中查找城市ID
    cityId = find_city_id(city)
    if not cityId:
        print(f"未找到城市 '{city}' 的ID，请检查城市名称是否正确")
        return []

    print(f"找到城市ID: {cityId}")

    print(f"\n开始获取 {city}的景点数据...")
    # 获取景点信息
    # spots = get_spots_by_search(city, 20)
    spots = get_spots_name(city,300, cityId)
    #
    # # 如果主要方案失败，使用备用方案
    # if not spots or len(spots) == 0:
    #     print("主要方案获取失败，尝试备用方案...")
    #     spots = get_spots_by_search(city, 20)

    if not spots:
        print("未获取到任何景点数据，程序结束。")
        return []

    # 保存到CSV文件
    save_spots_to_file(spots, city)

    # 提取景点名称列表
    spot_names = [spot["景点"] for spot in spots]

    if not spot_names:
        print("未成功")

    print(f"\n成功获取 {len(spot_names)} 个景点")
    # return spot_names  # 返回景点名称列表
    return city
# 出现问题
# 1.api发生变化，返回的attractionlist长度为0
# 解决方案:尝试使用新的api参数(json_data)。没起效果应该是ip被封，间隔一个星期爬取失败，一个月之后重新爬取时成功
#2. 获得的数据精准度不够，包含景点之外的数据
# 解决:在保存前查询景点类型，精准筛选不标准的数据
# 3.返回的景点类型为逗号间隔的列表形式，需要进行处理后才能正确载入数据库
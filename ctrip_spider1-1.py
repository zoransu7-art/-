'''
ctrip_spider1-1:携程评论爬虫第2个进程的补充部分，景点介绍爬取
读取 ctrip_spider0 生成的 {城市}_携程景点.csv，并根据详情页抓取景点介绍保存到csv表格
'''

import csv
import os
import time
import requests
import random
from fake_useragent import UserAgent
from urllib.parse import quote
import re
from bs4 import BeautifulSoup
import json

# ===================== 配置 =====================
MAX_RETRY = 3  # 最大重试次数
RETRY_INTERVAL = 5  # 重试间隔(秒)
DELAY_MIN = 1.5  # 最小延迟(秒)
DELAY_MAX = 4  # 最大延迟(秒)
BATCH_SIZE = 10  # 每处理10个景点输出一次进度


# ===================== 辅助函数 =====================
def clean_text(text):
    """清理文本，移除多余空格和换行"""
    if not text:
        return ""
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 替换多个空白字符为单个空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_random_headers():
    """生成随机请求头"""
    ua = UserAgent()
    return {
        'authority': 'you.ctrip.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': ua.chrome
    }


def extract_introduction_from_html(html_content, spot_name):
    """
    从HTML中提取景点介绍
    根据您提供的HTML结构专门优化
    返回: (介绍内容, 提取方式)
    """
    soup = BeautifulSoup(html_content, 'html.parser')


    # 方式1: 从moduleContent中提取 (根据您提供的HTML结构)
    # 尝试查找class包含"moduleContent"的div
    module_contents = soup.find_all('div', class_=re.compile(r'moduleContent'))

    for module_content in module_contents:
        # 查找LimitHeightText
        limit_height = module_content.find('div', class_=re.compile(r'LimitHeightText'))
        if limit_height:
            paragraphs = limit_height.find_all('p')
            if paragraphs:
                introduction = ' '.join([p.get_text(strip=True) for p in paragraphs])
                if introduction.strip():
                    return clean_text(introduction), "方式1: moduleContent > LimitHeightText > p"

    # 方式2: 从特定结构 body > div.__next > div.sight-detail > div.detailWrapper > div.introductionBox.exposure > p.introductionText 提取
    # 查找class包含"introductionBox"的div
    introduction_boxes = soup.find_all('div', class_=re.compile(r'introductionBox'))

    for intro_box in introduction_boxes:
        # 查找class包含"introductionText"的p标签
        intro_text_ps = intro_box.find_all('p', class_=re.compile(r'introductionText'))

        for p_tag in intro_text_ps:
            text = p_tag.get_text(strip=True)
            if text and len(text) > 10:  # 至少10字符才认为是介绍
                return clean_text(text), "方式2: introductionBox > introductionText"

    # 方式3: 查找所有LimitHeightText，然后判断哪个包含景点介绍
    limit_height_texts = soup.find_all('div', class_=re.compile(r'LimitHeightText'))

    # 收集所有可能的介绍文本
    possible_introductions = []

    for limit_height in limit_height_texts:
        # 获取所有p标签
        paragraphs = limit_height.find_all('p')
        if paragraphs:
            text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            if text.strip() and len(text) > 10:  # 至少10字符才认为是介绍
                # 检查文本中是否包含一些关键词，判断是否是景点介绍
                keywords = ['位于', '景点', '景区', '介绍', '简介', '风景', '特色']
                if any(keyword in text for keyword in keywords):
                    possible_introductions.append((text, limit_height))

    # 如果有多个可能，选择最长的那个（最可能是完整介绍）
    if possible_introductions:
        possible_introductions.sort(key=lambda x: len(x[0]), reverse=True)
        best_intro = possible_introductions[0][0]
        return clean_text(best_intro), "方式3: LimitHeightText查找(多个)"

    # 方法4: 查找moduleContent中的文本内容
    module_contents = soup.find_all('div', class_=re.compile(r'moduleContent'))

    for module_content in module_contents:
        # 检查moduleContent前面是否有包含"介绍"的moduleTitle
        prev_sibling = module_content.find_previous_sibling('div', class_=re.compile(r'moduleTitle'))
        if prev_sibling and ('介绍' in prev_sibling.get_text() or '简介' in prev_sibling.get_text()):
            # 查找LimitHeightText
            limit_height = module_content.find('div', class_=re.compile(r'LimitHeightText'))
            if limit_height:
                paragraphs = limit_height.find_all('p')
                if paragraphs:
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    if text.strip():
                        return clean_text(text), "方式4: moduleContent查找"

    # 方法5: 最后尝试，直接查找所有p标签，然后根据上下文判断
    all_paragraphs = soup.find_all('p')
    introduction_paragraphs = []

    for p in all_paragraphs:
        text = p.get_text(strip=True)
        # 判断这个p标签是否是介绍的一部分
        # 1. 长度适中（不是太短也不是太长）
        # 2. 包含景点相关词汇
        if 50 < len(text) < 1000:
            keywords = ['位于', '景点', '景区', '介绍', '风景', '特色', '建筑', '历史', '文化']
            if any(keyword in text for keyword in keywords):
                # 检查父元素是否是介绍结构的一部分
                parent_classes = []
                parent = p.parent
                for _ in range(5):  # 向上查找5层
                    if parent and parent.get('class'):
                        parent_classes.extend(parent.get('class'))
                    if parent:
                        parent = parent.parent

                if any(cls in ['moduleContent', 'LimitHeightText', 'detailModule'] for cls in parent_classes):
                    introduction_paragraphs.append(text)

    if introduction_paragraphs:
        # 按照原始顺序拼接
        all_text = soup.get_text()
        # 找出这些段落在完整文本中的位置
        positions = []
        for para in introduction_paragraphs:
            pos = all_text.find(para)
            if pos != -1:
                positions.append((pos, para))

        # 按位置排序并合并相邻段落
        positions.sort()
        merged_intro = ""
        last_pos = -100
        for pos, para in positions:
            if pos - last_pos < 100:  # 如果两个段落位置接近，认为是连续的
                if merged_intro:
                    merged_intro += " " + para
                else:
                    merged_intro = para
            else:
                if merged_intro:
                    break  # 如果已经有一段内容，且新段落距离较远，则停止
                merged_intro = para
            last_pos = pos

        if merged_intro:
            return clean_text(merged_intro), "方式5: 智能段落合并"

    # 如果所有方式都失败，保存HTML结构用于分析
    save_html_for_analysis(html_content, spot_name, soup)

    return "", "无法找到介绍内容"

def save_html_for_analysis(html_content, spot_name, soup):
    """保存HTML结构用于分析"""
    # 创建分析目录
    analysis_dir = "html_analysis"
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)

    # 清理文件名
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", spot_name)[:50]
    filename = f"{analysis_dir}/{safe_name}.html"

    # 保存完整的HTML
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 提取关键部分用于分析
    key_sections = []

    # 1. 查找所有div的class
    div_classes = set()
    for div in soup.find_all('div'):
        if div.get('class'):
            div_classes.add(' '.join(div.get('class')))

    # 2. 查找可能的介绍区域
    possible_intro_elements = []
    for text in ['介绍', '简介', '概况', '描述']:
        elements = soup.find_all(string=re.compile(text))
        for elem in elements:
            # 获取父级结构
            parent = elem.parent
            for _ in range(5):  # 向上查找5层
                if parent and parent.name == 'div' and parent.get('class'):
                    class_str = ' '.join(parent.get('class'))
                    possible_intro_elements.append({
                        'text': text,
                        'class': class_str,
                        'html': str(parent)[:500] + '...' if len(str(parent)) > 500 else str(parent)
                    })
                    break
                if parent:
                    parent = parent.parent

    # 保存分析报告
    analysis_file = f"{analysis_dir}/{safe_name}_analysis.txt"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write(f"景点: {spot_name}\n")
        f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")

        f.write("1. 所有div的class:\n")
        for cls in sorted(div_classes):
            f.write(f"   - {cls}\n")

        f.write("\n2. 可能的介绍区域:\n")
        for elem in possible_intro_elements:
            f.write(f"   - 包含文本 '{elem['text']}': class={elem['class']}\n")
            f.write(f"     部分HTML: {elem['html'][:200]}\n")

        # 3. 查找所有包含较长文本的div
        f.write("\n3. 包含较长文本的div (>100字符):\n")
        for div in soup.find_all('div'):
            text = div.get_text(strip=True)
            if len(text) > 100:
                classes = ' '.join(div.get('class')) if div.get('class') else '无class'
                f.write(f"   - class: {classes}\n")
                f.write(f"     文本预览: {text[:200]}...\n")

    print(f"    HTML分析已保存到: {analysis_file}")


def get_spot_introduction(detail_url, spot_name, max_retry=MAX_RETRY):
    """
    获取景点介绍
    :param detail_url: 景点详情页URL
    :param spot_name: 景点名称（用于保存分析文件）
    :param max_retry: 最大重试次数
    :return: 景点介绍文本
    """
    for retry in range(max_retry):
        try:
            # 随机延迟，避免请求过于频繁
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            # 生成随机请求头
            headers = get_random_headers()

            # 设置请求参数
            cookies = {
                'GUID': ''.join(str(random.randint(0, 9)) for _ in range(20)),
                '_RGUID': str(random.getrandbits(128)),
                'nfes_isSupportWebP': '1',
            }
            # url = detail_url+'?renderPlatform='
            # 发送请求
            response = requests.get(
                detail_url,
                headers=headers,
                cookies=cookies,
                timeout=30,
                allow_redirects=True
            )

            if response.status_code == 200:
                # 提取介绍
                introduction, method = extract_introduction_from_html(response.text, spot_name)

                if introduction:
                    print(f"    ✓ 成功获取景点介绍 ({method})，长度: {len(introduction)} 字符")
                    if len(introduction) > 200:
                        print(f"      预览: {introduction[:200]}...")
                    else:
                        print(f"      内容: {introduction}")
                    return introduction
                else:
                    print(f"    ✗ 未找到景点介绍内容 ({method})")
                    return ""
            else:
                print(f"    请求失败，状态码: {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"    请求超时 (第{retry + 1}次重试)")
        except requests.exceptions.RequestException as e:
            print(f"    请求异常: {e} (第{retry + 1}次重试)")
        except Exception as e:
            print(f"    处理异常: {e} (第{retry + 1}次重试)")

        # 重试前等待
        if retry < max_retry - 1:
            wait_time = RETRY_INTERVAL * (retry + 1)
            print(f"    等待{wait_time}秒后重试...")
            time.sleep(wait_time)

    print(f"    达到最大重试次数，跳过该景点")
    return ""


# ===================== 主函数 =====================
def get_introductions(city):
    """
    主函数：读取csv文件，获取所有景点的介绍
    :param city: 城市名称
    :return: 成功处理的景点数量
    """
    input_file = f"{city}_携程景点(已爬).csv"

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 未找到文件 {input_file}")
        return 0

    # 读取原始数据
    spots_data = []
    with open(input_file, 'r', encoding='gbk') as f:
        reader = csv.DictReader(f)
        for row in reader:
            spots_data.append(row)

    total_spots = len(spots_data)
    print(f"从 {input_file} 读取到 {total_spots} 个景点")

    # 检查是否有详情页URL
    if "详情页URL" not in spots_data[0]:
        print("错误: CSV文件中没有'详情页URL'列，请先运行ctrip_spider1.py")
        return 0

    # 获取介绍
    processed_count = 0
    success_count = 0

    print(f"\n开始获取景点介绍，详细信息将显示如下：")
    print(f"成功案例将显示提取方式和内容预览")
    print(f"失败案例将生成HTML分析文件在html_analysis目录中")
    print("="*60)

    for i, spot in enumerate(spots_data, 1):
        spot_name = spot.get("景点", "")
        detail_url = spot.get("详情页URL", "")

        print(f"\n[{i}/{total_spots}] 处理景点: {spot_name}")
        print(f"  URL: {detail_url}")

        if not detail_url:
            print(f"  ✗ 跳过: 无详情页URL")
            spot["景点介绍"] = ""
            continue

        # 获取景点介绍
        introduction = get_spot_introduction(detail_url, spot_name)
        spot["景点介绍"] = introduction

        processed_count += 1
        if introduction:
            success_count += 1

        # 批量保存进度（每处理10个或最后一批时保存）
        if i % BATCH_SIZE == 0 or i == total_spots:
            # 确定输出文件的字段名
            fieldnames = list(spots_data[0].keys())
            if "景点介绍" not in fieldnames:
                fieldnames.append("景点介绍")

            # 直接写入原文件（覆盖）
            with open(input_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(spots_data)

            print(f"\n=== 进度保存: {i}/{total_spots} ===")
            success_rate = (success_count / processed_count * 100) if processed_count > 0 else 0
            print(f"已成功获取 {success_count}/{processed_count} 个景点的介绍 (成功率: {success_rate:.1f}%)")

        # 随机延迟，避免请求过于频繁
        if i < total_spots:
            delay = random.uniform(0.5, 2)
            time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"处理完成!")
    print(f"总共处理: {processed_count} 个景点")
    print(f"成功获取介绍: {success_count} 个景点")
    success_rate = (success_count / processed_count * 100) if processed_count > 0 else 0
    print(f"成功率: {success_rate:.1f}%")

    # 如果存在失败案例，显示分析目录
    if success_count < processed_count:
        print(f"\n失败案例分析:")
        print(f"  1. 查看html_analysis目录中的分析文件")
        print(f"  2. 每个失败景点会生成两个文件:")
        print(f"     - [景点名].html: 完整的HTML页面")
        print(f"     - [景点名]_analysis.txt: 分析报告，包含所有div的class和可能的介绍区域")

    return success_count


def main():
    """主程序"""
    print("携程景点介绍爬虫 - 增强分析版")
    print("="*50)
    print("说明:")
    print("1. 成功案例将显示提取方式和内容预览")
    print("2. 失败案例将在html_analysis目录生成分析文件")
    print("3. 分析文件包含HTML结构和所有可能的介绍区域")
    print("="*50)

    # 查找可用的城市文件
    import glob
    city_files = glob.glob("*_携程景点(已爬).csv")

    if not city_files:
        print("未找到任何城市景点文件，请先运行 ctrip_spider0.py")
        return

    # 选择城市文件
    print("\n检测到以下城市景点文件:")
    for i, file in enumerate(city_files, 1):
        city = file.replace("*_携程景点(已爬).csv", "")
        print(f"{i}. {city}")

    if len(city_files) == 1:
        city = city_files[0].replace("*_携程景点(已爬).csv", "")
        print(f"\n自动选择城市: {city}")
    else:
        try:
            choice = int(input("\n请选择城市文件序号: ")) - 1
            if 0 <= choice < len(city_files):
                city = city_files[choice].replace("*_携程景点(已爬).csv", "")
            else:
                print("选择无效，请手动输入城市名称")
                city = input("请输入城市名称: ").strip()
        except ValueError:
            print("输入无效，请手动输入城市名称")
            city = input("请输入城市名称: ").strip()

    # 开始获取介绍
    print(f"\n开始获取 {city} 的景点介绍...")
    print("="*60)

    get_introductions(city)


if __name__ == "__main__":
    main()

'''
只有方法2和4在成功获取简介'''
import os
import requests
from bs4 import BeautifulSoup
import re
from collections import defaultdict
import json
import time  # 确保导入time模块

# Cloudflare API配置信息
CF_API_KEY = os.getenv('CF_API_KEY')
CF_ZONE_ID = os.getenv('CF_ZONE_ID')
CF_DOMAIN_NAME = os.getenv('CF_DOMAIN_NAME')
CF_API_EMAIL = os.getenv('CF_API_EMAIL')

# 定义请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 定义五个网址
urls = [
    "https://cf.090227.xyz/",
    "https://ip.164746.xyz/",
    "https://monitor.gacjie.cn/page/cloudflare/ipv4.html",
    "https://jkapi.com/api/cf_best?server=1&type=v4"
]

# 解析延迟数据的正则表达式
latency_pattern = re.compile(r'(\d+(\.\d+)?)\s*(ms|毫秒)?')

# 运营商关键词映射
ISP_KEYWORDS = {
    '移动': ['移动', 'CMCC', 'CM', '中国移动'],
    '联通': ['联通', 'CUCC', 'CU', '中国联通', '网通'],
    '电信': ['电信', 'CTCC', 'CT', '中国电信']
}

def isp_classifier(line_name):
    """根据线路名称分类运营商"""
    line_name = line_name.lower()
    for isp, keywords in ISP_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in line_name:
                return isp
    return '其他'

def extract_table_data(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            if "jkapi.com" in url:
                return response.json()  # 直接返回JSON数据
            else:
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
        else:
            print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
    return None

def process_site_data(url):
    data = extract_table_data(url)
    if not data:
        return []

    if "jkapi.com" in url:
        # 处理JSON格式的API数据
        result = []
        if data.get('status') and data.get('code') == 200:
            info = data.get('info', {})
            for isp_key in ['CM', 'CU', 'CT']:
                for item in info.get(isp_key, []):
                    result.append({
                        'ip': item.get('ip', ''),
                        'line_name': item.get('line_name', ''),
                        'latency': item.get('delay', 0),
                        'isp': isp_classifier(item.get('line_name', ''))
                    })
        return result
    elif isinstance(data, BeautifulSoup):
        # 原有的HTML处理逻辑
        html_data = data
        data_list = []
        if "cf.090227.xyz" in url:
            rows = html_data.find_all('tr')
            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 3:
                    line_name = columns[0].text.strip()
                    ip_address = columns[1].text.strip()
                    latency_text = columns[2].text.strip()
                    latency_match = latency_pattern.match(latency_text)
                    if latency_match:
                        latency_value = float(latency_match.group(1))
                        isp = isp_classifier(line_name)
                        data_list.append({
                            'ip': ip_address,
                            'line_name': line_name,
                            'latency': latency_value,
                            'isp': isp
                        })

        elif "ip.164746.xyz" in url:
            rows = html_data.find_all('tr')
            for row in rows:
                columns = row.find_all('td')
                if len(columns) >= 5:
                    ip_address = columns[0].text.strip()
                    line_name = "未知线路"
                    latency_text = columns[4].text.strip()
                    latency_match = latency_pattern.match(latency_text)
                    if latency_match:
                        latency_value = float(latency_match.group(1))
                        isp = isp_classifier(line_name)
                        data_list.append({
                            'ip': ip_address,
                            'line_name': line_name,
                            'latency': latency_value,
                            'isp': isp
                        })

        elif "monitor.gacjie.cn" in url:
            rows = html_data.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 5:
                    line_name = tds[0].text.strip()
                    ip_address = tds[1].text.strip()
                    latency_text = tds[4].text.strip()
                    latency_match = latency_pattern.match(latency_text)
                    if latency_match:
                        latency_value = float(latency_match.group(1))
                        isp = isp_classifier(line_name)
                        data_list.append({
                            'ip': ip_address,
                            'line_name': line_name,
                            'latency': latency_value,
                            'isp': isp
                        })
        return data_list
    return []

def filter_and_sort_ips(data):
    """筛选并排序IP，按运营商分类"""
    # 按运营商分类
    isp_data = defaultdict(list)
    
    for item in data:
        if item['isp'] in ISP_KEYWORDS:  # 只处理三大运营商的IP
            isp_data[item['isp']].append(item)
    
    # 对每个运营商的IP按延迟排序
    for isp in isp_data:
        isp_data[isp].sort(key=lambda x: x['latency'])
    
    # 获取每个运营商前10个IP
    result = {}
    for isp in ['移动', '电信', '联通']:  # 确保顺序一致
        result[isp] = isp_data.get(isp, [])[:10]
    
    return result

def save_to_file(isp_ips):
    """将筛选后的IP保存到文件"""
    with open('yx_ips.txt', 'w', encoding='utf-8') as f:
        for isp, ips in isp_ips.items():
            f.write(f"# {isp} IP列表 (共{len(ips)}个)\n")
            for ip_info in ips:
                line = f"{ip_info['ip']}#{ip_info['line_name']}-{ip_info['latency']}ms\n"
                f.write(line)
            f.write("\n")

def get_all_ips(isp_ips):
    """获取所有要添加的IP地址"""
    all_ips = []
    for isp, ips in isp_ips.items():
        all_ips.extend([ip['ip'] for ip in ips])
    return all_ips

def clear_dns_records():
    """清空DNS记录"""
    print("开始清空所有DNS记录...")
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }

    params = {"per_page": 1000}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        records = response.json().get('result', [])
        print(f"找到 {len(records)} 条DNS记录需要删除...")
        
        deleted_count = 0
        for record in records:
            if record['name'] == CF_DOMAIN_NAME or record['name'].endswith(f".{CF_DOMAIN_NAME}"):
                delete_url = f"{url}/{record['id']}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 200:
                    print(f"成功删除DNS记录: {record['name']} ({record['type']})")
                    deleted_count += 1
                    time.sleep(0.5)  # 添加短暂延迟避免速率限制
                else:
                    print(f"删除DNS记录失败: {record['id']}, 状态码: {delete_response.status_code}")
                    print(f"错误详情: {delete_response.json().get('errors', '未知错误')}")
        
        print(f"共删除 {deleted_count}/{len(records)} 条DNS记录")
        time.sleep(5)  # 等待删除操作完全生效
    else:
        print(f"获取DNS记录失败，状态码: {response.status_code}")
        print(f"错误详情: {response.json().get('errors', '未知错误')}")

def check_record_exists(ip):
    """检查记录是否已存在"""
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }
    
    params = {
        "name": CF_DOMAIN_NAME,
        "type": "A",
        "content": ip
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            records = response.json().get('result', [])
            return len(records) > 0
    except Exception as e:
        print(f"检查记录存在时出错: {str(e)}")
    return False

def add_dns_record(ip):
    """添加DNS记录"""
    # 首先检查记录是否已存在
    if check_record_exists(ip):
        print(f"记录已存在，跳过添加: {ip}")
        return True
    
    print(f"正在添加DNS记录: {ip}")
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }
    
    # 验证IP地址格式
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        print(f"无效的IP地址格式: {ip}")
        return False
    
    data = {
        "type": "A",
        "name": CF_DOMAIN_NAME,
        "content": ip,
        "ttl": 1,  # 使用1表示自动TTL
        "proxied": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        
        if response.status_code == 200:
            print(f"成功创建DNS记录: {ip}")
            return True
        else:
            print(f"创建DNS记录失败: {ip}, 状态码: {response.status_code}")
            print(f"错误详情: {response_data.get('errors', '未知错误')}")
            return False
    except Exception as e:
        print(f"创建DNS记录时发生异常: {str(e)}")
        return False

def main():
    all_data = []
    for url in urls:
        print(f"正在处理 {url}...")
        site_data = process_site_data(url)
        all_data.extend(site_data)
        print(f"从 {url} 获取到 {len(site_data)} 条IP记录")

    # 筛选并排序IP
    isp_ips = filter_and_sort_ips(all_data)
    
    # 保存到文件
    save_to_file(isp_ips)
    
    # 打印统计信息
    for isp in ['移动', '电信', '联通']:
        ips = isp_ips.get(isp, [])
        print(f"找到 {isp} IP {len(ips)} 个" + (f"，最低延迟: {ips[0]['latency']}ms" if ips else ""))

    # 执行DNS操作
    clear_dns_records()
    all_ips = get_all_ips(isp_ips)
    print(f"准备添加 {len(all_ips)} 条DNS记录...")
    
    # 添加延迟避免速率限制
    time.sleep(5)
    
    success_count = 0
    for ip in all_ips:
        if add_dns_record(ip):
            success_count += 1
        time.sleep(1)  # 控制添加速度
    
    print(f"DNS记录添加完成，成功添加 {success_count}/{len(all_ips)} 条记录")

if __name__ == "__main__":
    main()

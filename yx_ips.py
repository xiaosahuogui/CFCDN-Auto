import os
import requests
from bs4 import BeautifulSoup
import re

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
    "https://stock.hostmonit.com/CloudFlareYes",
    "https://ip.164746.xyz/"
]

# 解析延迟数据的正则表达式
latency_pattern = re.compile(r'(\d+(\.\d+)?)\s*(ms|毫秒)?')

# 提取表格数据的函数
def extract_table_data(url):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
        else:
            print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
    return None

# 处理每个网址的数据
def process_site_data(url):
    soup = extract_table_data(url)
    if not soup:
        return []

    data = []
    if "cf.090227.xyz" in url:
        rows = soup.find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 3:
                line_name = columns[0].text.strip()
                ip_address = columns[1].text.strip()
                latency_text = columns[2].text.strip()
                latency_match = latency_pattern.match(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    latency_unit = 'ms'
                    data.append(f"{ip_address}#{line_name}-{latency_value}{latency_unit}")

    elif "stock.hostmonit.com" in url:
        rows = soup.find_all('tr', class_=re.compile(r'el-table__row'))
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 3:
                line_name = columns[0].text.strip()
                ip_address = columns[1].text.strip()
                latency_text = columns[2].text.strip()
                latency_match = latency_pattern.match(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    latency_unit = 'ms'
                    data.append(f"{ip_address}#{line_name}-{latency_value}{latency_unit}")

    elif "ip.164746.xyz" in url:
        rows = soup.find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 5:
                ip_address = columns[0].text.strip()
                latency_text = columns[4].text.strip()
                latency_match = latency_pattern.match(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    latency_unit = 'ms'
                    data.append(f"{ip_address}-{latency_value}{latency_unit}")

    elif "monitor.gacjie.cn" in url:
        rows = soup.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 5:
                line_name = tds[0].text.strip()
                ip_address = tds[1].text.strip()
                latency_text = tds[4].text.strip()
                latency_match = latency_pattern.match(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    latency_unit = 'ms'
                    data.append(f"{ip_address}#{line_name}-{latency_value}{latency_unit}")

    elif "345673.xyz" in url:
        rows = soup.find_all('tr', class_=re.compile(r'line-cm|line-ct|line-cu'))
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 4:
                line_name = tds[0].text.strip()
                ip_address = tds[1].text.strip()
                latency_text = tds[3].text.strip()
                latency_match = latency_pattern.match(latency_text)
                if latency_match:
                    latency_value = latency_match.group(1)
                    latency_unit = 'ms'
                    data.append(f"{ip_address}#{line_name}-{latency_value}{latency_unit}")

    return data

# 主函数，处理所有网站的数据
def main():
    all_data = []
    for url in urls:
        site_data = process_site_data(url)
        all_data.extend(site_data)

    # 去除重复的IP地址行
    unique_data = list(set(all_data))

    # 过滤延迟数据低于100ms的行
    filtered_data = [line for line in unique_data if float(line.split('-')[-1].replace('ms', '')) < 100]

    # 写入到yx_ips.txt文件
    with open('yx_ips.txt', 'w', encoding='utf-8') as f:
        for line in filtered_data:
            f.write(line + '\n')

    # 执行清空DNS记录的操作
    clear_dns_records()
    
    # 从yx_ips.txt文件中提取IPv4地址
    with open("yx_ips.txt", "r") as file:
        ip_lines = [line.strip() for line in file if line.strip()]
        ipv4 = [line.split('#')[0] for line in ip_lines if '#' in line]
    
    # 只取前200个IP地址
    ipv4 = ipv4[:200]
    
    print(f"准备添加 {len(ipv4)} 条DNS记录...")
    
    # 执行添加DNS记录的操作
    for ip in ipv4:
        add_dns_record(ip)

# 清空CF_DOMAIN_NAME的所有DNS记录
def clear_dns_records():
    print("开始清空所有DNS记录...")
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }

    params = {
        "per_page": 1000  # 确保获取所有记录
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        records = response.json().get('result', [])
        print(f"找到 {len(records)} 条DNS记录需要删除...")
        
        for record in records:
            # 只删除与我们的域名匹配的记录
            if record['name'] == CF_DOMAIN_NAME or record['name'].endswith(f".{CF_DOMAIN_NAME}"):
                delete_url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record['id']}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 200:
                    print(f"成功删除DNS记录: {record['name']} ({record['type']})")
                else:
                    print(f"删除DNS记录失败: {record['id']}, 状态码: {delete_response.status_code}, 响应: {delete_response.text}")
    else:
        print(f"获取DNS记录失败, 状态码: {response.status_code}, 响应: {response.text}")

# 添加新的IPv4地址为DNS记录
def add_dns_record(ip):
    print(f"正在添加DNS记录: {ip}")
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CF_API_KEY}",
        "X-Auth-Email": CF_API_EMAIL,
        "Content-Type": "application/json"
    }
    data = {
        "type": "A",
        "name": CF_DOMAIN_NAME,
        "content": ip,
        "ttl": 60,  # 设置TTL为1分钟
        "proxied": False
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"成功创建DNS记录: {ip}")
    else:
        print(f"创建DNS记录失败: {ip}, 状态码: {response.status_code}, 响应: {response.text}")

if __name__ == "__main__":
    main()

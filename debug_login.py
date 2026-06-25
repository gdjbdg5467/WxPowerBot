#!/usr/bin/env python3
"""
微信登录调试脚本 — 监控完整的扫码登录流程
"""
import re, time, json, logging, sys
import requests
from http.client import HTTPConnection

# 启用 HTTP 调试
HTTPConnection.debuglevel = 1
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('wx_debug')

s = requests.Session()
BASE = 'https://login.weixin.qq.com'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 1. 获取 UUID
log.info('=== Step 1: 获取 UUID ===')
params = {
    'appid': 'wx782c26e4c19acffb',
    'fun': 'new',
    'redirect_uri': 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?mod=desktop',
    'lang': 'zh_CN'
}
r = s.get(f'{BASE}/jslogin', params=params, headers={'User-Agent': UA})
log.info(f'jslogin: {r.text[:300]}')
m = re.search(r'uuid = "(.+?)"', r.text)
uuid = m.group(1) if m else ''
log.info(f'UUID: {uuid}')

# 2. 生成 QR URL
qr_url = f'https://login.weixin.qq.com/l/{uuid}'
log.info(f'QR URL: {qr_url}')

# 3. 轮询扫码状态
log.info('=== Step 2: 等待扫码 (约2分钟有效) ===')
last_code = None
start = time.time()
while time.time() - start < 150:
    t = int(time.time())
    check_url = f'{BASE}/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid={uuid}&tip=1&r={int(-t/1579)}&_={t}'
    r = s.get(check_url, headers={'User-Agent': UA})
    m = re.search(r'window.code=(\d+)', r.text)
    code = m.group(1) if m else 'unknown'
    if code != last_code:
        elapsed = int(time.time() - start)
        log.info(f'[{elapsed}s] code={code}')
        last_code = code
    if code == '201':
        log.info('=== ✅ 已扫码！请按手机上确认按钮 ===')
    elif code == '200':
        log.info('=== 🎉 用户已确认登录！ ===')
        log.info(f'Full login response: {r.text[:500]}')
        
        # 解析 redirect_uri
        m2 = re.search(r'window.redirect_uri="(.+?)"', r.text)
        if m2:
            redirect_uri = m2.group(1)
            log.info(f'Redirect URI: {redirect_uri}')
            
            # 用 UOS 头访问 redirect_uri
            uos_headers = {
                'User-Agent': UA,
                'client-version': '2.0.0',
                'extspam': 'Go8FCIkFEokFCggwMDAwMDAwMRAGGvAESySibk50w5Wb3uTl2c2h64jVVrV7gNs06GFlWplHQbY/5FfiO++1yH4ykCyNPWKXmco+wfQzK5R98D3so7rJ5LmGFvBLjGceleySrc3SOf2Pc1gVehzJgODeS0lDL3/I/0S2SSE98YgKleq6Uqx6ndTy9yaL9qFxJL7eiA/R3SEfTaW1SBoSITIu+EEkXff+Pv8NHOk7N57rcGk1w0ZzrRQDkXTOXFN2iHYIzAAZPIOY45Lsh+A4slpgnDiaOvRtlQYCt97nmPLuTipOJ8Qc5pM7ZsOsAPPrCQL7nK0I7aPrFDF0q4ziUUKettzW8MrAaiVfmbD1/VkmLNVqqZVvBCtRblXb5FHmtS8FxnqCzYP4WFvz3T0TcrOqwLX1M/DQvcHaGGw0B0y4bZMs7lVScGBFxMj3vbFi2SRKbKhaitxHfYHAOAa0X7/MSS0RNAjdwoyGHeOepXOKY+h3iHeqCvgOH6LOifdHf/1aaZNwSkGotYnYScW8Yx63LnSwba7+hESrtPa/huRmB9KWvMCKbDThL/nne14hnL277EDCSocPu3rOSYjuB9gKSOdVmWsj9Dxb/iZIe+S6AiG29Esm+/eUacSba0k8wn5HhHg9d4tIcixrxveflc8vi2/wNQGVFNsGO6tB5WF0xf/plngOvQ1/ivGV/C1Qpdhzznh0ExAVJ6dwzNg7qIEBaw+BzTJTUuRcPk92Sn6QDn2Pu3mpONaEumacjW4w6ipPnPw+g2TfywJjeEcpSZaP4Q3YV5HG8D6UjWA4GSkBKculWpdCMadx0usMomsSS/74QgpYqcPkmamB4nVv1JxczYITIqItIKjD35IGKAUwAA==',
                'referer': 'https://wx.qq.com/?&lang=zh_CN&target=t'
            }
            r2 = s.get(redirect_uri, headers=uos_headers, allow_redirects=False)
            log.info(f'Redirect status: {r2.status_code}')
            log.info(f'Redirect headers: {dict(r2.headers)}')
            log.info(f'Redirect body: {r2.text[:500]}')
            
            # 尝试解析 skey/pass_ticket
            skey = re.findall('<skey>(.*?)</skey>', r2.text, re.S)
            pt = re.findall('<pass_ticket>(.*?)</pass_ticket>', r2.text, re.S)
            wxsid = re.findall('<wxsid>(.*?)</wxsid>', r2.text, re.S)
            wxuin = re.findall('<wxuin>(.*?)</wxuin>', r2.text, re.S)
            log.info(f'skey={skey}, pass_ticket={pt}, wxsid={wxsid}, wxuin={wxuin}')
            
            if skey and pt:
                log.info('=== ✅ 登录信息解析成功！ ===')
            else:
                log.info('=== ❌ 登录信息解析失败 ===')
                # 尝试不带 UOS 头
                log.info('Trying WITHOUT UOS headers...')
                r3 = s.get(redirect_uri, headers={'User-Agent': UA}, allow_redirects=False)
                log.info(f'Without UOS: status={r3.status_code}, body={r3.text[:500]}')
                
                # 尝试用 luvletter2333 的 extspam
                alt_extspam = 'Go8FCIkFEokFCggwMDAwMDAwMRAGGvAESySibk50w5Wb3uTl2c2h64jVVrV7gNs06GFlWplHQbY/5FfiO++1yH4ykCyNPWKXmco+wfQzK5R98D3so7rJ5LmGFvBLjGceleySrc3SOf2Pc1gVehzJgODeS0lDL3/I/0S2SSE98YgKleq6Uqx6ndTy9yaL9qFxJL7eiA/R3SEfTaW1SBoSITIu+EEkXff+Pv8NHOk7N57rcGk1w0ZzrRQDkXTOXFN2iHYIzAAZPIOY45Lsh+A4slpgnDiaOvRtlQYCt97nmPLuTipOJ8Qc5pM7ZsOsAPPrCQL7nK0I7aPrFDF0q4ziUUKettzW8MrAaiVfmbD1/VkmLNVqqZVvBCtRblXb5FHmtS8FxnqCzYP4WFvz3T0TcrOqwLX1M/DQvcHaGGw0B0y4bZMs7lVScGBFxMj3vbFi2SRKbKhaitxHfYHAOAa0X7/MSS0RNAjdwoyGHeOepXOKY+h3iHeqCvgOH6LOifdHf/1aaZNwSkGotYnYScW8Yx63LnSwba7+hESrtPa/huRmB9KWvMCKbDThL/nne14hnL277EDCSocPu3rOSYjuB9gKSOdVmWsj9Dxb/iZIe+S6AiG29Esm+/eUacSba0k8wn5HhHg9d4tIcixrxveflc8vi2/wNQGVFNsGO6tB5WF0xf/plngOvQ1/ivGV/C1Qpdhzznh0ExAVJ6dwzNg7qIEBaw+BzTJTUuRcPk92Sn6QDn2Pu3mpONaEumacjW4w6ipPnPw+g2TfywJjeEcpSZaP4Q3YV5HG8D6UjWA4GSkBKculWpdCMadx0usMomsSS/74QgpYqcPkmamB4nVv1JxczYITIqItIKjD35IGKAUwAA=='
                r4 = s.get(redirect_uri, headers={**uos_headers, 'extspam': alt_extspam}, allow_redirects=False)
                log.info(f'Alt extspam: status={r4.status_code}, body={r4.text[:500]}')
        break
    elif code == '400':
        elapsed = int(time.time() - start)
        log.info(f'[{elapsed}s] ❌ 二维码过期或登录失败')
        break
    elif code == '408':
        pass  # 正常等待
    time.sleep(1)

log.info(f'Final cookies: {dict(s.cookies)}')
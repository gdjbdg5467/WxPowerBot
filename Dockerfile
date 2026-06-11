FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============ itchat-uos 升级 & 补丁 ============
# 升级到 1.5.0.dev0（更新 UOS_PATCH_EXTSPAM 密钥）
RUN pip install --no-cache-dir "itchat-uos==1.5.0.dev0"

# 补丁 1: cookies 回退（避免 KeyError: wxsid/wxuin）
RUN sed -i 's/cookies\["wxsid"\]/cookies.get("wxsid","")/g; s/cookies\["wxuin"\]/cookies.get("wxuin","")/g' \
    /usr/local/lib/python3.11/site-packages/itchat/components/login.py

# 补丁 2: redirect_uri 空值保护 + skey/pass_ticket 异常保护 + 慢速轮询
RUN python3 <<'PYEOF'
import re

path = '/usr/local/lib/python3.11/site-packages/itchat/components/login.py'
with open(path) as f:
    c = f.read()

# redirect_uri guard
old1 = "    regx = r'window.redirect_uri=\"(\\S+)\";'\n    core.loginInfo['url'] = re.search(regx, loginContent).group(1)"
new1 = "    regx = r'window.redirect_uri=\"(\\S+)\";'\n    m = re.search(regx, loginContent)\n    if not m:\n        logger.error('Failed to parse redirect_uri: %s' % loginContent[:300])\n        core.isLogging = False\n        return False\n    core.loginInfo['url'] = m.group(1)"
if old1 in c:
    c = c.replace(old1, new1)
    print("Patch 1 (redirect_uri guard): OK")
else:
    print("Patch 1: NOT FOUND")

# skey/pass_ticket guard
old2 = "    skey = re.findall('<skey>(.*?)</skey>', r.text, re.S)[0]\n    pass_ticket = re.findall(\n        '<pass_ticket>(.*?)</pass_ticket>', r.text, re.S)[0]"
new2 = "    try:\n        skey = re.findall('<skey>(.*?)</skey>', r.text, re.S)[0]\n        pass_ticket = re.findall(\n            '<pass_ticket>(.*?)</pass_ticket>', r.text, re.S)[0]\n    except (IndexError, AttributeError):\n        logger.error('Failed to parse skey/pass_ticket from login response: %s' % r.text[:300])\n        core.isLogging = False\n        return False"
if old2 in c:
    c = c.replace(old2, new2)
    print("Patch 2 (skey/pass_ticket guard): OK")
else:
    print("Patch 2: NOT FOUND")

# 补丁 3: 慢速轮询（微信限流保护）
old3 = "        isLoggedIn = False\\n        while not isLoggedIn:\\n            status = self.check_login()\\n            if hasattr(qrCallback, '__call__'):\\n                qrCallback(uuid=self.uuid, status=status,\\n                           qrcode=qrStorage.getvalue())"
new3 = "        isLoggedIn = False\\n        while not isLoggedIn:\\n            status = self.check_login()\\n            if hasattr(qrCallback, '__call__'):\\n                qrCallback(uuid=self.uuid, status=status,\\n                           qrcode=qrStorage.getvalue())\\n            time.sleep(0.8)"
if old3 in c:
    c = c.replace(old3, new3)
    print("Patch 3 (slow polling): OK")
else:
    print("Patch 3: NOT FOUND")

with open(path, 'w') as f:
    f.write(c)
print("Patches complete")
PYEOF

COPY bot.py handlers.py tg_forward.py cftc.py lsposed.py werss.py main.py config.yaml ./
COPY admin/ admin/

VOLUME ["/data"]

EXPOSE 8646

ENV WXPOWERBOT_DATA_DIR=/data

CMD ["python3", "main.py"]
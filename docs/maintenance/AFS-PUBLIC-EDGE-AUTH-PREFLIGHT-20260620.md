# AFS 公网入口认证预检 - 2026-06-20

## 范围

本文记录当前内测公网入口的认证阻断点，并给出可重复预检方法。

边界：

- 不写入 secret、邀请码、cookie 或 provider key。
- 不触发 provider 调用。
- 不写入 Company OS 私有源材料。
- 只记录仓库可公开的执行投影。

## 当前结论

代码、GitHub、服务器 `/home`、服务器 `/opt` 已经可以保持同一提交。

Runtime 在 Nginx 后面是正常的：

```text
http://127.0.0.1:8790/health
=> status=ready
=> auth_required=true
=> studio_static.status=ready
```

但公网入口仍在 Runtime 之前被 Nginx Basic Auth 拦截：

```text
https://afstudio.art/studio/
=> 401 Unauthorized
=> WWW-Authenticate: Basic realm="AFS Studio Internal Test"
```

所以用户看到的登录循环不是 Studio 前端登录逻辑错误，也不是 Runtime app auth 失效，而是公网边缘层仍有一层旧的 Basic Auth。

## 新增预检命令

在本地 Codex 仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m tools.afs_public_edge_preflight `
  --public-url https://afstudio.art/studio/ `
  --server afs-bwg-ops `
  --report runs\public_edge_preflight_20260620.json
```

当前预期状态：

```text
blocked_by_edge_basic_auth
```

该命令在公网入口未就绪时会返回非零退出码，这是预期行为。

如果在服务器 `/opt/afs/AgentFlowStudio` 内直接运行，不需要再 SSH 回服务器，使用：

```bash
./.venv/bin/python -m tools.afs_public_edge_preflight \
  --public-url https://afstudio.art/studio/ \
  --check-runtime-health \
  --report runs/public_edge_preflight_server.json
```

## 服务器 sudo 修复步骤

只有在确认“产品登录应该交给 Runtime app auth / invite auth 处理”后，才执行下面的服务器命令。

```bash
sudo cp /etc/nginx/sites-available/afs-runtime /etc/nginx/sites-available/afs-runtime.bak-$(date +%Y%m%d%H%M%S)
sudo sed -i '/auth_basic "AFS Studio Internal Test";/d; /auth_basic_user_file \/etc\/nginx\/.htpasswd_afs;/d' /etc/nginx/sites-available/afs-runtime
sudo nginx -t
sudo systemctl reload nginx
```

注意：不要关闭 Runtime app 自身的账号、会话、邀请码认证。

## 修复后验证

先在服务器或本地检查公网响应：

```bash
curl -I https://afstudio.art/studio/
```

预期不再出现：

```text
WWW-Authenticate: Basic
```

再运行：

```powershell
.\.venv\Scripts\python.exe -m tools.afs_public_edge_preflight `
  --public-url https://afstudio.art/studio/ `
  --server afs-bwg-ops
```

或在服务器内运行：

```bash
./.venv/bin/python -m tools.afs_public_edge_preflight \
  --public-url https://afstudio.art/studio/ \
  --check-runtime-health
```

预期状态：

```text
ready_for_public_auth
```

## 该检查能证明什么

能证明：

- 公网边缘层没有继续拦截 Runtime auth。
- Runtime health 是 ready。
- Studio 静态资源已挂载。

不能证明：

- 邀请码注册已经通过。
- 用户登录全链路已经通过。
- 模型 provider 已经可用。
- 人工验收已经完成。
- 业务验证已经完成。

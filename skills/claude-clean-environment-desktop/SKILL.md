---
name: claude-clean-environment-desktop
description: 在电脑端（Windows / macOS / Linux）使用 Clash Verge 或 Mihomo 搭建干净稳定的 Claude 出海环境：通过“前置机场中转 + 干净静态 IP 链式出口”（或自有美国 VPS 直出）配合独立分流策略，完成公网 IP、DNS、IPv6 与 WebRTC 防漏验证。
---

# Claude 电脑端干净环境（Clash Verge / Mihomo）

搭建不触发风控的 Claude 环境，核心只做两件事：**1. 准备一个干净的静态 IP 出口；2. 配置 VPN 分流策略稳定接管流量**。

电脑端统一采用**“机场订阅 + 独立覆写（Override）文件”**维护，不要直接修改订阅生成的主 YAML，防止订阅刷新时冲掉自建出口和规则。

---

## 标准实操步骤

### 1. 准备干净的静态 IP 出口
- **首选方案（静态住宅 SOCKS5/HTTP 链式出口）**：购买干净独享的美国静态住宅代理（例如 NTT 静态住宅 IP）。因为静态住宅代理通常不能在国内直连，后续通过任意机场节点做前置中转（`dialer-proxy`）连过去。
- **备选方案（自有美国原生 VPS 直出）**：如果手里已有可直接出站且 IP 纯净的独享美国 VPS，无需再买静态住宅代理，直接看文末「附：自有美国 VPS 直接出口」。

### 2. 用独立覆写挂载链式出口节点
1. 将电脑端配置按职责拆分为独立覆写模块，避免订阅刷新覆盖：
   - `proxies`：追加购买的静态 SOCKS5 / HTTP 出口节点；
   - `groups`：定义两层核心代理组及分类组；
   - `rules`：挂载分流规则；
   - `merge`：统一设置 DNS、Fake-IP 与基础参数；
   - `script`（按需）：用于重命名带剩余流量/到期时间的动态订阅节点。
2. 在 `proxies` 覆写中添加静态出口节点，将 `dialer-proxy` 指向前置机场组 `↗️上游直连`：
   ```text
   电脑 -> ↗️上游直连（任意可用机场节点） -> 美国 NTT 链式出口（固定静态 IP） -> Claude / 目标网站
   ```
   ```yaml
   proxies:
     - name: 美国 NTT 链式出口
       type: socks5
       server: EXIT_HOST
       port: EXIT_PORT
       username: EXIT_USERNAME
       password: EXIT_PASSWORD
       dialer-proxy: ↗️上游直连
       udp: true
   ```
3. 注意事项：
   - `dialer-proxy` 的名称必须与前置代理组（或中转节点）名称完全一致。
   - 若服务商只提供 HTTP 代理，把 `type: socks5` 改为 `type: http`，不要猜测协议。
   - 不要把真实账号、密码、订阅 URL 或公网 IP 硬编码进公开仓库、Skill 或截图。

### 3. 套用 VPN 分流策略（见独立文件）
完整代理组模板、规则优先级顺序与订阅防覆盖规范，单独维护在 **[references/routing-strategy.md](references/routing-strategy.md)**，按该文件配置即可。核心要点如下：
1. **双层解耦**：核心只维护 `🔰国外流量`（选最终出口）和 `↗️上游直连`（选机场前置节点）两层；选中 `美国 NTT 链式出口` 后，切换任意机场节点只改变中继路线，最终公网 IP 始终固定不变。
2. **AI 规则前置**：Claude、OpenAI、Google AI 及 `browserleaks.com` 等域名规则必须排在 `GEOSITE,cn`、`GEOIP,CN` 之前，末尾用 `MATCH` 兜底。
3. **禁用全局模式**：始终使用**规则模式（Rule）**，不要开全局模式（Global），否则国内流量也会白白消耗静态出口带宽。

### 4. 开启接管与防漏验证
1. **选择接管方式**：仅浏览器使用时走本地 HTTP / SOCKS5 系统代理即可；需要接管 Claude 桌面客户端或命令行工具时，在规则模式下开启 **TUN 模式**。
2. **核对命中日志**：在客户端连接面板访问目标站点，确认连接日志实际命中 `美国 NTT 链式出口`（或预期静态节点）。浏览器测试通过不代表所有桌面应用都走了同一路径，桌面端应用需按域名单独看一眼连接记录。
3. **BrowserLeaks 四项检查**：打开 `browserleaks.com` 依次检查 IP、IPv6、DNS、WebRTC：
   - HTTP Public IP 与 WebRTC Public IP 必须一致，且等于你购买的静态出口 IP；
   - IPv6 无公网地址泄露；
   - DNS 列表不出现国内本地运营商 DNS。
4. **区分私有地址**：WebRTC 的 Local IP 若出现 `192.168.0.0/16`、`10.0.0.0/8`、`172.16.0.0/12`，属于局域网或 TUN 虚拟网卡内网地址，**不是公网泄露**。
5. **UDP / QUIC 处理**：`udp: true` 仅代表允许客户端尝试转发 UDP，实际是否打通取决于前置机场和静态出口是否支持；若发现浏览器 QUIC 或 WebRTC 绕过代理，可在客户端开启“禁止非代理 UDP”。

---

## 附：备选模式——自有美国 VPS 直接出口

当订阅中的美国 VPS 本身就能国内直连且 IP 干净时，直接让它作为最终出口，**不要加 `dialer-proxy`，也不要再套一层 SOCKS5**：

1. 机场/自建订阅节点名常带有动态流量或到期时间，先在 `script` 覆写里重命名为固定名称 `美国 VPS 直连`：
   ```javascript
   function main(config) {
     const prefix = "VPS_NODE_PREFIX";
     const stableName = "美国 VPS 直连";
     const proxies = Array.isArray(config.proxies) ? config.proxies : [];
     const node = proxies.find(item =>
       item && typeof item.name === "string" && item.name.startsWith(prefix)
     );
     if (!node) return config;
     node.name = stableName;
     config.proxies = proxies.filter(item => item !== node && item.name !== stableName);
     config.proxies.push(node);
     return config;
   }
   ```
2. 在 `🔰国外流量` 代理组中将该 `美国 VPS 直连` 设为首选即可，其余分流规则与第 3、4 步完全一致。

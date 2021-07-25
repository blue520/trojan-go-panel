# trojan-go-panel
trojan-go 多用户多节点管理面板

## 进度😋
所有的基础功能全部完成！后面就是修修补补的小版本了

(；′⌒`) 前端写的越来越乱了, 后面有时间用NaiveUI重写一遍

## 部署

部署之前建议先更新包仓库

`yum update||apt-get update`

### 已通过测试的系统

- CentOS 7 64 Bit

### 暂不支持的系统

- Debian

### 主节点部署

`source <(curl -sL https://git.io/install-trojan)`

### 子节点部署
`source <(curl -sL https://git.io/install-trojan) --worknode 子节点域名 主节点域名 子节点名称 主节点数据库密码`

## 展示

地址: [demo.emzvpn.xyz](http://demo.emzvpn.xyz/)

用户: admin

密码: demopasswd

### 多节点管理
![node](./.github/source/node.png)
### 多用户管理
![user](./.github/source/user.png)
### 用户限制以及增删节点
![edit-user](./.github/source/edit-user.png)
### 查看链接及订阅
![trojan-url](./.github/source/trojan-url.png)

## 画大饼

- [x] 实装日期限制与流量限制  2021-07-05
- [x] 删除子节点  2021-07-07
- [x] 主节点启用 trojan  2021-07-10
- [x] 动态 clash 订阅链接  2021-07-11
- [ ] 定时巡检子节点, 出现异常则邮件通知管理员
- [ ] 子节点测速
- [ ] 子节点分组与子节点查询
- [ ] 子节点简要信息（目前节点信息占用空间太大，节点一多就很乱）
- [ ] 主节点与子节点改用 https 协议
- [ ] 监控子节点 trojan 状态
- [ ] 面板控制节点升级、重启
- [ ] 各节点可选独立部署数据库，减少主节点IO压力
- [ ] 用户权限自由配置
- [ ] 通过面板自动部署子节点
- [ ] 子节点 trojan 日志查看
- [ ] 优化面板响应速度
- [ ] 安全加固


## 开发手册

想共同开发或是自己魔改的小伙伴可以参阅开发手册

[开发手册](https://github.com/ermaozi/trojan-go-panel/wiki/%E5%BC%80%E5%8F%91%E6%89%8B%E5%86%8C)

## 致谢

感谢所有支持、参与此项目的同学。

<details>
<summary>致谢名单</summary>

| 时间 | 称呼 | 说明 |
| ---- | ---- | ---- |
| 2021-07-03 | **我媳妇** | 媳妇看我天天肝到两点钟实在辛苦，赞助10元红包。在此答谢。|

</details>


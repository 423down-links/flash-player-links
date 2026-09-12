# Adobe Flash Player 离线安装包下载

自动获取 Adobe Flash Player 国内特供版的最新版本号和完整离线安装包下载地址。

## 功能

- 实时从官方 API（api.flash.cn）获取最新在线安装器版本
- 自动检测最新可用的完整离线安装包版本（官方不定期上传）
- 提供 ActiveX / PPAPI / NPAPI 三个版本的下载链接
- 离线包直链支持 IDM 等下载工具直接下载（无需 Referer）
- GitHub Actions 每日自动检测更新

## 版本说明

| 类型 | 说明 |
|------|------|
| 在线安装器 | 最新版本，约 2.3MB，运行后自动下载完整包安装 |
| 完整离线包 | 官方不定期上传，约 11-22MB，可直接安装无需联网 |

## 离线包地址格式

```
https://www.flash.cn/flashplayer/{版本号}/install_flash_player_ax_cn.exe     (ActiveX/IE)
https://www.flash.cn/flashplayer/{版本号}/install_flash_player_ppapi_cn.exe  (PPAPI/Chrome)
https://www.flash.cn/flashplayer/{版本号}/install_flash_player_cn.exe         (NPAPI/Firefox)
```

版本号格式：`34.0.0.380` → `3400380`

## 自动更新

GitHub Actions 每日北京时间 8:00 自动运行 `flash_player_check_offline.py`，检测最新可用离线包版本并更新页面。

## 本地运行

```bash
python3 flash_player_check_offline.py
```

## 访问地址

https://423down.github.io/flash-player-links/

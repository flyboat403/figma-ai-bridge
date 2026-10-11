# -*- coding: utf-8 -*-
"""figma-ai-bridge 一键部署 / 体检（Windows）

用法:
  python setup_windows.py                 部署到默认位置 ~/.workbuddy-ai/tools/figma-bridge
  python setup_windows.py --target <dir>  部署到自定义目录（测试用）
  python setup_windows.py --check         只体检，不做任何改动

部署内容: vendor 下的中继（socket.ts）+ 打过补丁的 Figma 插件 → 桥接目录，
并生成「启动桥接.vbs / 停止桥接.bat / 使用说明.txt」。
缺 Bun 时自动从 npmmirror 下载官方二进制安装（仅 Windows x64）。
"""
import argparse, io, os, shutil, socket, sys, tempfile, urllib.request, zipfile

HOME = os.path.expanduser("~")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(SKILL_DIR, "vendor")
DEFAULT_TARGET = os.path.join(HOME, ".workbuddy-ai", "tools", "figma-bridge")
BUN_EXE = os.path.join(HOME, ".bun", "bin", "bun.exe")
BUN_VERSION = "1.4.3"
BUN_URL = ("https://registry.npmmirror.com/-/binary/bun/bun-v%s/"
           "bun-windows-x64.zip" % BUN_VERSION)


def log(msg):
    print("[figma-ai-bridge] " + msg)


def winpath(p):
    """统一为 Windows 反斜杠绝对路径（VBS/BAT 里不混用正斜杠）"""
    return os.path.abspath(p).replace("/", "\\")


def check_bun():
    if os.path.exists(BUN_EXE):
        return BUN_EXE
    p = shutil.which("bun") or shutil.which("bun.exe")
    return p


def install_bun():
    log("未检测到 Bun，尝试从 npmmirror 下载官方二进制 v" + BUN_VERSION)
    dest = os.path.join(HOME, ".bun", "bin")
    os.makedirs(dest, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="bun_dl_")
    zpath = os.path.join(tmp, "bun.zip")
    try:
        urllib.request.urlretrieve(BUN_URL, zpath)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
        found = 0
        for root, _dirs, files in os.walk(tmp):
            for fn in files:
                if fn.lower() in ("bun.exe", "bunx.exe"):
                    shutil.copy2(os.path.join(root, fn), os.path.join(dest, fn))
                    found += 1
        if found < 1:
            log("!! 压缩包中未找到 bun.exe，请手动安装：https://bun.sh/docs/installation")
            return None
    except Exception as e:
        log("!! 自动安装失败（%s）。请手动安装 Bun：https://bun.sh/docs/installation" % e)
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bunfig = os.path.join(HOME, ".bunfig.toml")
    if not os.path.exists(bunfig):
        with io.open(bunfig, "w", encoding="utf-8") as f:
            f.write('[install]\nregistry = "https://registry.npmmirror.com"\n')
    log("Bun 安装完成：" + BUN_EXE)
    return BUN_EXE if os.path.exists(BUN_EXE) else check_bun()


def port_listening(port=3055):
    try:
        with socket.socket() as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def write_launchers(target, bun):
    repo = winpath(os.path.join(target, "repo"))
    bun = winpath(bun)
    logf = winpath(os.path.join(target, "socket.log"))
    # VBS 用纯 ASCII 注释，避免任何编码问题
    vbs = (
        "' ============================================================\n"
        "'  Figma bridge - start relay (hidden window)\n"
        "'  listens on ws://localhost:3055 ; log -> socket.log\n"
        "' ============================================================\n"
        "Set sh = CreateObject(\"WScript.Shell\")\n"
        "ret = sh.Run(\"cmd /c cd /d \"\"{repo}\"\" && \"\"{bun}\"\" run src\\socket.ts"
        " >> \"\"{log}\"\" 2>&1\", 0, False)\n"
    ).format(repo=repo, bun=bun, log=logf)
    with io.open(os.path.join(target, "启动桥接.vbs"), "w", encoding="gbk") as f:
        f.write(vbs)

    bat = (
        "@ECHO off\r\n"
        "setlocal enabledelayedexpansion\r\n"
        "set KILLED=0\r\n"
        "echo [Figma bridge] stopping relay (port 3055)...\r\n"
        "for /f \"tokens=5\" %%P in ('netstat -ano ^| findstr \":3055\" ^| findstr \"LISTENING\"') do (\r\n"
        "  echo   Killing PID %%P ...\r\n"
        "  taskkill /PID %%P /F\r\n"
        "  set KILLED=1\r\n"
        ")\r\n"
        "if \"!KILLED!\"==\"0\" echo   [info] nothing listening on 3055\r\n"
        "echo done.\r\n"
        "pause\r\n"
    )
    with io.open(os.path.join(target, "停止桥接.bat"), "w", encoding="gbk") as f:
        f.write(bat)


def write_readme(target):
    txt = """Figma 桥接 使用说明
====================
【目录】{target}
  启动桥接.vbs   双击启动中继服务（端口 3055，后台运行）
  停止桥接.bat   停止中继服务
  socket.log     运行日志（排障先看这里）
  repo\\          中继源码 + 本地开发版 Figma 插件

【Figma 插件导入（一次性）】
  1. 打开 Figma 桌面版 → 菜单 Figma → Plugins → Development → Import plugin from manifest…
  2. 选择文件：{manifest}
  3. 之后每次运行：Plugins → Development → Cursor MCP Plugin → Connect

【每次使用】
  1. 双击「启动桥接.vbs」
  2. Figma 运行插件，面板显示 Connected to server in channel: XXXXXXXX
     ★★ 面板保持开着：不要关、不要按 Esc、不要切换插件/文件 ★★
  3. 把频道号告诉 AI，直接说需求（读稿 / 改稿 / 导出图）

【排查】
  端口检查：netstat -ano | findstr 3055
  日志检查：看 socket.log
  完整手册：技能包 references\\全流程手册.md
""".format(target=winpath(target),
           manifest=winpath(os.path.join(target, "repo", "src", "cursor_mcp_plugin", "manifest.json")))
    with io.open(os.path.join(target, "使用说明.txt"), "w", encoding="gbk") as f:
        f.write(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=None, help="部署目录（默认 ~/.workbuddy-ai/tools/figma-bridge）")
    ap.add_argument("--check", action="store_true", help="只体检，不改动")
    args = ap.parse_args()
    target = args.target or DEFAULT_TARGET

    print("=" * 60)
    log("体检：")
    bun = check_bun()
    log("  Bun 运行时      : %s" % (bun or "缺失"))
    log("  桥接目录        : %s%s" % (target, "" if os.path.isdir(target) else "（不存在）"))
    log("  中继端口 3055   : %s" % ("监听中" if port_listening() else "未监听"))
    log("  技能 vendor 目录: %s%s" % (VENDOR, "" if os.path.isdir(VENDOR) else "（缺失！技能包不完整）"))
    print("=" * 60)

    if args.check:
        if not bun:
            log("→ 需要先安装 Bun：运行本脚本（去掉 --check）可自动安装")
        if not os.path.isdir(target):
            log("→ 需要部署：运行本脚本（去掉 --check）")
        if os.path.isdir(target) and not port_listening():
            log("→ 部署好了但中继没跑：双击「启动桥接.vbs」")
        return

    if not os.path.isdir(VENDOR):
        log("!! 技能包不完整（缺 vendor），无法部署")
        sys.exit(1)

    if not bun:
        bun = install_bun()
    if not bun:
        sys.exit(1)

    # 1) 复制 vendor → 桥接目录
    src_dir = os.path.join(target, "repo", "src")
    os.makedirs(src_dir, exist_ok=True)
    shutil.copy2(os.path.join(VENDOR, "socket.ts"), os.path.join(src_dir, "socket.ts"))
    plug_dst = os.path.join(src_dir, "cursor_mcp_plugin")
    os.makedirs(plug_dst, exist_ok=True)
    plug_src = os.path.join(VENDOR, "cursor_mcp_plugin")
    for fn in os.listdir(plug_src):
        shutil.copy2(os.path.join(plug_src, fn), os.path.join(plug_dst, fn))
    log("已部署中继与插件 → %s" % src_dir)

    # 2) 生成启停脚本与说明
    write_launchers(target, bun)
    write_readme(target)
    log("已生成 启动桥接.vbs / 停止桥接.bat / 使用说明.txt")

    print("=" * 60)
    log("部署完成！接下来：")
    log("  1. 双击「%s\\启动桥接.vbs」启动中继" % target)
    log("  2. Figma → Plugins → Development → Import plugin from manifest…")
    log("     选择：%s" % os.path.join(plug_dst, "manifest.json"))
    log("  3. 运行插件 Connect，把频道号发给 AI；面板保持开着")
    print("=" * 60)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""auto_watcher.py — 监听中继日志，自动对"插件加入的频道"发起秒级探测
运行: python auto_watcher.py   （常驻；从日志末尾开始跟随）

识别逻辑:
  中继日志里 "裸格式 join"（{"type":"join","channel":...}，无 Command 字段）
  = Figma 插件本体（区别于 MCP 客户端带 Command 的 join）
  一旦某个裸 join 成功加入频道 → 自动拉起 probe_daemon.py <channel>
"""
import io, os, re, subprocess, sys, time

HOME = os.path.expanduser("~")
BRIDGE = os.path.join(HOME, ".workbuddy-ai", "tools", "figma-bridge")
LOG = os.path.join(BRIDGE, "socket.log")
SELF_LOG = os.path.join(BRIDGE, "_auto_watcher.log")
PY = sys.executable or "python"


def log(msg):
    line = time.strftime("[%m-%d %H:%M:%S] ") + msg
    print(line, flush=True)
    try:
        with io.open(SELF_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    log("watcher BEGIN (following %s)" % LOG)
    fired = {}
    daemons = {}

    while True:
        try:
            with io.open(LOG, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, os.SEEK_END)
                cur_type, has_cmd = None, False
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(1)
                        for ch in [c for c, p in daemons.items() if p.poll() is not None]:
                            daemons.pop(ch, None)
                        continue
                    line = line.rstrip("\n")
                    if line.startswith("=== Received message"):
                        cur_type, has_cmd = None, False
                    elif line.startswith("Type: "):
                        m = re.match(r"Type: (\w+)", line)
                        if m:
                            cur_type = m.group(1)
                    elif line.startswith("Command: "):
                        has_cmd = True
                    elif "Client joined channel" in line:
                        m = re.search(r'Client joined channel "([^"]+)" \((\d+) total', line)
                        if m and cur_type == "join" and not has_cmd:
                            ch = m.group(1)
                            if ch in daemons and daemons[ch].poll() is None:
                                continue
                            if time.time() - fired.get(ch, 0) < 120:
                                continue
                            fired[ch] = time.time()
                            log("FIRE probe for channel %s (plugin join detected)" % ch)
                            try:
                                daemons[ch] = subprocess.Popen(
                                    [PY, os.path.join(BRIDGE, "probe_daemon.py"), ch],
                                    creationflags=(0x08000000 if os.name == "nt" else 0),
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except Exception as e:
                                log("fire failed: %s" % e)
        except FileNotFoundError:
            time.sleep(2)
        except Exception as e:
            log("watcher error: %s" % e)
            time.sleep(2)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""probe_daemon.py — 常驻秒级文档探测器（配合 auto_watcher.py 使用）
用法: python probe_daemon.py <channel> [--interval 5] [--max-min 30]

行为:
  - 启动 MCP 服务（bun x cursor-talk-to-figma-mcp）并加入频道
  - 每 interval 秒发一次 get_document_info 轮询
  - 插件在线并回包时，把文档信息写入 _probe_hits.log（追加、带时间戳）
"""
import json, subprocess, sys, threading, time, queue, os, io

HOME = os.path.expanduser("~")
BUN = os.path.join(HOME, ".bun", "bin", "bun.exe")
ARGS = ["x", "cursor-talk-to-figma-mcp@latest"]
BRIDGE = os.path.join(HOME, ".workbuddy-ai", "tools", "figma-bridge")
HITS = os.path.join(BRIDGE, "_probe_hits.log")


def log(msg):
    line = time.strftime("[%m-%d %H:%M:%S] ") + msg
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with io.open(HITS, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    args = list(sys.argv[1:])
    if not args:
        print("用法: python probe_daemon.py <channel> [--interval N] [--max-min N]")
        return
    channel = args[0]
    interval, max_min = 5.0, 30.0
    for i, a in enumerate(args):
        if a == "--interval" and i + 1 < len(args):
            interval = float(args[i + 1])
        if a == "--max-min" and i + 1 < len(args):
            max_min = float(args[i + 1])

    log("daemon BEGIN ch=%s interval=%ss max=%smin" % (channel, interval, max_min))
    proc = subprocess.Popen(
        [BUN] + ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
        bufsize=1, creationflags=(0x08000000 if os.name == "nt" else 0))
    q = queue.Queue()

    def rd(stream):
        try:
            for line in stream:
                q.put(line.rstrip())
        except Exception:
            pass

    threading.Thread(target=rd, args=(proc.stdout,), daemon=True).start()

    def send(obj):
        try:
            proc.stdin.write(json.dumps(obj) + "\n")
            proc.stdin.flush()
            return True
        except Exception:
            return False

    def wait_id(want, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                line = q.get(timeout=1)
            except queue.Empty:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("id") == want:
                return obj
        return None

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                         "clientInfo": {"name": "wb-daemon", "version": "0.1"}}})
        r = wait_id(1, 90)
        log("initialize: %s" % ("OK" if r else "FAIL"))
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(1)

        joined = False
        for _ in range(10):
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "join_channel", "arguments": {"channel": channel}}})
            r = wait_id(2, 30)
            if r and "Successfully joined" in json.dumps(r):
                joined = True
                break
            time.sleep(2)
        log("joined channel: %s" % joined)
        if not joined:
            log("FATAL: cannot join channel, exiting")
            return

        next_id = 1000
        pending = {}
        hits = 0
        polls = 0
        t_end = time.time() + max_min * 60
        last_status = time.time()

        while time.time() < t_end:
            if proc.poll() is not None:
                log("FATAL: MCP server exited")
                return
            next_id += 1
            send({"jsonrpc": "2.0", "id": next_id, "method": "tools/call",
                  "params": {"name": "get_document_info", "arguments": {}}})
            pending[next_id] = time.time()
            polls += 1

            drain_until = time.time() + interval
            while time.time() < drain_until:
                try:
                    line = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                rid = obj.get("id")
                if rid not in pending:
                    continue
                del pending[rid]
                if "result" in obj:
                    try:
                        text = obj["result"]["content"][0]["text"]
                    except Exception:
                        text = json.dumps(obj, ensure_ascii=False)
                    if "timed out" in text.lower():
                        pass  # 插件不在线（等待超时）
                    elif text.lower().startswith("error"):
                        pass  # 其他错误
                    else:
                        hits += 1
                        log("HIT #%d ch=%s ====\n%s\n====" % (hits, channel, text[:4000]))

            if time.time() - last_status > 60:
                last_status = time.time()
                log("alive: polls=%d hits=%d pending=%d" % (polls, hits, len(pending)))
            for k in [k for k, t in pending.items() if time.time() - t > 150]:
                del pending[k]

        log("daemon END ch=%s (max time reached)" % channel)
    finally:
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    main()

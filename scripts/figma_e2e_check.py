# -*- coding: utf-8 -*-
"""figma_e2e_check.py — 端到端检查：加入指定频道并读取 Figma 文档信息与当前选择

用法:
  python figma_e2e_check.py <channel>

说明:
  - 依赖：中继服务（端口 3055）已运行 + Figma 插件已在该频道里显示 Connected
  - 会启动一个 MCP 服务进程（bun x cursor-talk-to-figma-mcp@latest），
    完成 initialize →（等待连接就绪）→ join_channel（带重试）→ get_document_info → get_selection
"""
import json, socket, subprocess, sys, threading, time, queue, os

HOME = os.path.expanduser("~")
BUN = os.path.join(HOME, ".bun", "bin", "bun.exe")
if os.path.exists(BUN):
    ARGS = ["x", "cursor-talk-to-figma-mcp@latest"]
else:
    BUN = os.path.join(HOME, "AppData", "Roaming", "npm", "bunx.cmd")
    ARGS = ["cursor-talk-to-figma-mcp@latest"]


def port_open(port=3055):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else None
    if not channel:
        print("用法: python figma_e2e_check.py <channel>")
        sys.exit(1)
    print("relay 3055:", "UP" if port_open() else "DOWN (请先启动中继!)")

    cmd = [BUN] + ARGS
    print("spawn:", " ".join(cmd))
    flags = 0x08000000 if os.name == "nt" else 0
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", bufsize=1, creationflags=flags)
    q = queue.Queue()

    def rd(stream, kind):
        for line in stream:
            q.put((kind, line.rstrip()))
        q.put((kind, None))

    threading.Thread(target=rd, args=(proc.stdout, "out"), daemon=True).start()
    threading.Thread(target=rd, args=(proc.stderr, "err"), daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def drain_print(limit=8):
        n = 0
        while n < limit:
            try:
                kind, line = q.get_nowait()
            except queue.Empty:
                break
            if line is not None:
                print("  [%s] %s" % (kind, line[:220]))
                n += 1

    def wait_for_id(want, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            try:
                kind, line = q.get(timeout=1)
            except queue.Empty:
                continue
            if line is None:
                continue
            if kind == "out":
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
                         "clientInfo": {"name": "wb-e2e", "version": "0.1"}}})
        r = wait_for_id(1, 90)
        print("initialize:", "OK" if r else "FAIL")
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 等 MCP 服务与中继完成 WebSocket 连接
        print("等待连接稳定…")
        time.sleep(3)

        joined = False
        for i in range(6):
            send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                  "params": {"name": "join_channel", "arguments": {"channel": channel}}})
            r = wait_for_id(3, 30)
            txt = json.dumps(r, ensure_ascii=False) if r else "(no resp)"
            print("join 尝试%d:" % (i + 1), txt[:260])
            if r and "Error" not in txt:
                joined = True
                break
            time.sleep(2)
        print("JOINED:", joined)

        if joined:
            send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                  "params": {"name": "get_document_info", "arguments": {}}})
            r = wait_for_id(4, 60)
            print("==== 文档信息 ====")
            print(json.dumps(r, ensure_ascii=False)[:1200] if r else "FAIL")
            send({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                  "params": {"name": "get_selection", "arguments": {}}})
            r = wait_for_id(5, 60)
            print("==== 当前选择 ====")
            print(json.dumps(r, ensure_ascii=False)[:800] if r else "FAIL")
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        print("(server stopped)")
        # ---- 附：中继日志相关行（含断连代码与时间戳）----
        try:
            import io
            log = os.path.join(HOME, ".workbuddy-ai", "tools", "figma-bridge", "socket.log")
            if os.path.exists(log):
                with io.open(log, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                keep = [l.rstrip() for l in lines[-500:]
                        if ("joined channel" in l or "Client closed" in l
                            or "New client connected" in l or "heartbeat" in l
                            or "No other clients" in l or "Broadcast" in l)]
                print("==== 中继日志（最近相关 %d 行）====" % len(keep[-30:]))
                for l in keep[-30:]:
                    print("  " + l)
            else:
                print("(relay log not found: %s)" % log)
        except Exception as e:
            print("(relay log read failed: %s)" % e)


if __name__ == "__main__":
    main()

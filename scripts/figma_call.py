# -*- coding: utf-8 -*-
"""figma_call.py — 通用调用器：加入频道并调用任意 Figma MCP 工具（支持批量）

用法:
  python figma_call.py <channel> <tool> [json_args]
  python figma_call.py <channel> --batch "[{\"tool\":\"get_document_info\",\"args\":{}}, ...]"
"""
import json, socket, subprocess, sys, threading, time, queue, os

HOME = os.path.expanduser("~")
BUN = os.path.join(HOME, ".bun", "bin", "bun.exe")
ARGS = ["x", "cursor-talk-to-figma-mcp@latest"]
if not os.path.exists(BUN):
    BUN = os.path.join(HOME, "AppData", "Roaming", "npm", "bunx.cmd")
    ARGS = ["cursor-talk-to-figma-mcp@latest"]


def port_open(port=3055):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    channel = sys.argv[1]
    if sys.argv[2] == "--batch":
        batch = json.loads(sys.argv[3])
    else:
        tool = sys.argv[2]
        targs = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        batch = [{"tool": tool, "args": targs}]

    print("relay:", "UP" if port_open() else "DOWN")
    flags = 0x08000000 if os.name == "nt" else 0
    proc = subprocess.Popen([BUN] + ARGS, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", bufsize=1, creationflags=flags)
    q = queue.Queue()

    def rd(stream, kind):
        for line in stream:
            q.put((kind, line.rstrip()))

    threading.Thread(target=rd, args=(proc.stdout, "out"), daemon=True).start()
    threading.Thread(target=rd, args=(proc.stderr, "err"), daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def wait_for_id(want, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            try:
                kind, line = q.get(timeout=1)
            except queue.Empty:
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
                         "clientInfo": {"name": "wb-call", "version": "0.1"}}})
        r = wait_for_id(1, 90)
        print("initialize:", "OK" if r else "FAIL")
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(3)
        joined = False
        for i in range(6):
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "join_channel", "arguments": {"channel": channel}}})
            r = wait_for_id(2, 30)
            txt = json.dumps(r, ensure_ascii=False) if r else ""
            if r and "Error" not in txt:
                joined = True
                break
            time.sleep(2)
        print("JOINED:", joined)
        if not joined:
            return
        nid = 10
        for item in batch:
            tool = item.get("tool")
            targs = item.get("args") or {}
            nid += 1
            send({"jsonrpc": "2.0", "id": nid, "method": "tools/call",
                  "params": {"name": tool, "arguments": targs}})
            r = wait_for_id(nid, 120)
            print("==== %s ====" % tool)
            if r is None:
                print("FAIL (no response)")
            else:
                try:
                    parts = []
                    for c in r["result"]["content"]:
                        if not isinstance(c, dict):
                            continue
                        if c.get("type") == "image" and c.get("data"):
                            import base64
                            img_path = os.path.join(
                                HOME, ".workbuddy-ai", "tools", "figma-bridge",
                                "_export_%s.png" % tool)
                            with open(img_path, "wb") as f:
                                f.write(base64.b64decode(c["data"]))
                            parts.append("(IMAGE SAVED: %s, %d bytes, mime=%s)" % (
                                img_path, os.path.getsize(img_path), c.get("mimeType")))
                        else:
                            parts.append(c.get("text", ""))
                    txt = "\n".join(parts)
                except Exception:
                    txt = json.dumps(r, ensure_ascii=False)
                # 完整结果落盘，便于全文检索
                try:
                    outp = os.path.join(HOME, ".workbuddy-ai", "tools", "figma-bridge", "_last_%s.txt" % tool)
                    with open(outp, "w", encoding="utf-8") as f:
                        f.write(txt)
                    print("(full saved: %s, %d chars)" % (outp, len(txt)))
                except Exception as e:
                    print("(save failed: %s)" % e)
                print(txt[:4000])
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        print("(done)")


if __name__ == "__main__":
    main()

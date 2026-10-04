import sys, json, struct, socket

def send_message(message):
    encoded = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    length = struct.unpack('@I', raw_length)[0]
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode('utf-8'))

def forward_to_app(url):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", 49152))
        payload = json.dumps({"url": url}) + "\n"
        s.sendall(payload.encode('utf-8'))
        s.close()
        return True
    except Exception as e:
        return False

def main():
    msg = read_message()
    if msg and "url" in msg:
        ok = forward_to_app(msg["url"])
        send_message({"status": "SUCCESS" if ok else "APP_NOT_REACHABLE", "url": msg["url"]})

if __name__ == '__main__':
    main()

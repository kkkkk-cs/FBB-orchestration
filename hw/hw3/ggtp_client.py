#!/usr/bin/env python3
import argparse, socket, sys

HOST = "127.0.0.1"
PORT = 5000
BUF_SIZE = 2048


def exchange(sock, address, message, timeout, retries):
    sock.settimeout(timeout)
    for n in range(1, retries + 1):
        print("send:", message)
        sock.sendto(message.encode(), address)
        try:
            data, _ = sock.recvfrom(BUF_SIZE)
            reply = data.decode(errors="replace").strip()
            print("recv:", reply)
            return reply
        except socket.timeout:
            print(f"timeout {n}/{retries}", file=sys.stderr)
    return None


def parse_welcome(text):
    parts = text.split()
    if len(parts) != 3 or parts[0] != "WLCM":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def play(host, port, timeout, retries):
    address = (host, port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        reply = exchange(sock, address, f"HELO {timeout}", timeout, retries)
        if reply is None:
            print("server does not answer", file=sys.stderr)
            return 1

        interval = parse_welcome(reply)
        if interval is None:
            print("bad welcome message:", reply, file=sys.stderr)
            return 1

        left, right = interval
        while left <= right:
            middle = (left + right) // 2
            reply = exchange(sock, address, f"GUES {middle}", timeout, retries)

            if reply is None:
                print("server does not answer", file=sys.stderr)
                return 1
            if reply == "MORE":
                left = middle + 1
            elif reply == "LESS":
                right = middle - 1
            elif reply.startswith("BING "):
                print("success")
                print("key:", reply.split(maxsplit=1)[1])
                return 0
            elif reply == "FAIL":
                print("server returned FAIL", file=sys.stderr)
                return 1
            else:
                print("unexpected reply:", reply, file=sys.stderr)
                return 1

    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--retries", type=int, default=5)
    args = parser.parse_args()
    raise SystemExit(play(args.host, args.port, args.timeout, args.retries))


if __name__ == "__main__":
    main()


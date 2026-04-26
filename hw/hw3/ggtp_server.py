#!/usr/bin/env python3
import argparse, binascii, hashlib, math, random, socket, time

HOST = "127.0.0.1"
PORT = 5000
BUF_SIZE = 2048
TTL = 300


def seed_by_ip(ip):
    return binascii.crc32(ip.encode()) & 0xffffffff


def make_game(ip):
    rng = random.Random(seed_by_ip(ip))
    low = 1
    high = rng.randint(100, 1000)
    target = rng.randint(low, high)
    return {
        "low": low,
        "high": high,
        "target": target,
        "limit": math.ceil(math.log2(high - low + 1)) + 1,
        "used": 0,
        "updated": time.monotonic(),
        "last_guess": None,
        "last_reply": None,
    }


def key_for(ip, target):
    return hashlib.sha256(f"{ip}:{target}".encode()).hexdigest()


def cleanup(games):
    now = time.monotonic()
    for ip in list(games):
        if now - games[ip]["updated"] > TTL:
            del games[ip]


def valid_timeout(value):
    try:
        return float(value) > 0
    except ValueError:
        return False


def handle_helo(parts, ip, games):
    if len(parts) not in (1, 2):
        return "FAIL"
    if len(parts) == 2 and not valid_timeout(parts[1]):
        return "FAIL"

    if ip not in games:
        games[ip] = make_game(ip)

    game = games[ip]
    game["updated"] = time.monotonic()
    reply = f'WLCM {game["low"]} {game["high"]}'
    game["last_reply"] = reply
    return reply


def handle_gues(parts, ip, games):
    if len(parts) != 2 or ip not in games:
        return "FAIL"

    game = games[ip]
    game["updated"] = time.monotonic()

    try:
        guess = int(parts[1])
    except ValueError:
        return "FAIL"

    if guess == game["last_guess"] and game["last_reply"]:
        return game["last_reply"]

    if game["used"] >= game["limit"]:
        games.pop(ip, None)
        return "FAIL"

    game["used"] += 1
    game["last_guess"] = guess

    if guess < game["target"]:
        game["last_reply"] = "MORE"
        return "MORE"
    if guess > game["target"]:
        game["last_reply"] = "LESS"
        return "LESS"

    reply = "BING " + key_for(ip, game["target"])
    games.pop(ip, None)
    return reply


def process(message, ip, games):
    cleanup(games)
    parts = message.strip().split()
    if not parts:
        return "FAIL"
    if parts[0] == "HELO":
        return handle_helo(parts, ip, games)
    if parts[0] == "GUES":
        return handle_gues(parts, ip, games)
    return "FAIL"


def serve(host, port):
    games = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))
        print(f"GGTP socket server on {host}:{port}")
        while True:
            data, addr = sock.recvfrom(BUF_SIZE)
            ip, p = addr
            message = data.decode(errors="replace").strip()
            reply = process(message, ip, games)
            print(f"{ip}:{p} | {message} -> {reply}")
            sock.sendto(reply.encode(), addr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()


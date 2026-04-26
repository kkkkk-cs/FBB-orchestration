#!/usr/bin/env python3
import argparse, asyncio, binascii, hashlib, math, random, time

HOST = "127.0.0.1"
PORT = 5001
TTL = 300


def seed(ip):
    return binascii.crc32(ip.encode()) & 0xffffffff


def make_state(ip):
    rnd = random.Random(seed(ip))
    low = 1
    high = rnd.randint(100, 1000)
    target = rnd.randint(low, high)
    return {
        "low": low,
        "high": high,
        "target": target,
        "limit": math.ceil(math.log2(high - low + 1)) + 1,
        "attempts": 0,
        "time": time.monotonic(),
        "last_number": None,
        "last_answer": None,
    }


def make_key(ip, target):
    return hashlib.sha256(f"{ip}:{target}".encode()).hexdigest()


class Protocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.games = {}

    def connection_made(self, transport):
        self.transport = transport
        print("Async GGTP server started")

    def clear_old(self):
        now = time.monotonic()
        for ip in list(self.games):
            if now - self.games[ip]["time"] > TTL:
                del self.games[ip]

    def helo(self, parts, ip):
        if len(parts) not in (1, 2):
            return "FAIL"
        if len(parts) == 2:
            try:
                if float(parts[1]) <= 0:
                    return "FAIL"
            except ValueError:
                return "FAIL"

        if ip not in self.games:
            self.games[ip] = make_state(ip)

        game = self.games[ip]
        game["time"] = time.monotonic()
        answer = f'WLCM {game["low"]} {game["high"]}'
        game["last_answer"] = answer
        return answer

    def gues(self, parts, ip):
        if len(parts) != 2 or ip not in self.games:
            return "FAIL"

        game = self.games[ip]
        game["time"] = time.monotonic()

        try:
            guess = int(parts[1])
        except ValueError:
            return "FAIL"

        if guess == game["last_number"] and game["last_answer"]:
            return game["last_answer"]

        if game["attempts"] >= game["limit"]:
            self.games.pop(ip, None)
            return "FAIL"

        game["attempts"] += 1
        game["last_number"] = guess

        if guess < game["target"]:
            game["last_answer"] = "MORE"
            return "MORE"
        if guess > game["target"]:
            game["last_answer"] = "LESS"
            return "LESS"

        answer = "BING " + make_key(ip, game["target"])
        self.games.pop(ip, None)
        return answer

    def answer(self, message, ip):
        self.clear_old()
        parts = message.strip().split()
        if not parts:
            return "FAIL"
        if parts[0] == "HELO":
            return self.helo(parts, ip)
        if parts[0] == "GUES":
            return self.gues(parts, ip)
        return "FAIL"

    def datagram_received(self, data, addr):
        ip, port = addr
        message = data.decode(errors="replace").strip()
        reply = self.answer(message, ip)
        print(f"{ip}:{port} | {message} => {reply}")
        self.transport.sendto(reply.encode(), addr)


async def run(host, port):
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(Protocol, local_addr=(host, port))
    print(f"Listening on {host}:{port}")
    try:
        await asyncio.Future()
    finally:
        transport.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port))


if __name__ == "__main__":
    main()


import sys

side = "w"

for raw in sys.stdin:
    command = raw.strip()
    if command == "uci":
        print("id name FakePikafish", flush=True)
        print("option name MultiPV type spin default 1 min 1 max 10", flush=True)
        print("uciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("position fen "):
        side = command.split()[3]
    elif command.startswith("go "):
        moves = ("h2e2", "b0c2", "c3c4") if side == "w" else ("h7e7", "b9c7", "c6c5")
        print(f"info depth 11 multipv 1 score cp 30 nodes 600 pv {moves[0]}", flush=True)
        print(f"info depth 11 multipv 2 score cp 18 nodes 550 pv {moves[1]}", flush=True)
        print(f"info depth 11 multipv 3 score cp 8 nodes 500 pv {moves[2]}", flush=True)
        print(f"info depth 12 multipv 2 score cp 20 nodes 800 pv {moves[1]}", flush=True)
        print(f"info depth 12 multipv 1 score cp 35 nodes 1000 pv {moves[0]}", flush=True)
        print(f"info depth 12 multipv 3 score cp 10 nodes 700 pv {moves[2]}", flush=True)
        print(f"info depth 13 multipv 1 score cp 40 nodes 1200 pv {moves[0]}", flush=True)
        print(f"bestmove {moves[0]}", flush=True)
    elif command == "quit":
        break

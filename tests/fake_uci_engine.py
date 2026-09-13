import sys

for raw in sys.stdin:
    command = raw.strip()
    if command == "uci":
        print("id name FakePikafish", flush=True)
        print("option name MultiPV type spin default 1 min 1 max 10", flush=True)
        print("uciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("go "):
        print("info depth 12 multipv 2 score cp 20 nodes 800 pv b0c2 h9g7", flush=True)
        print("info depth 12 multipv 1 score cp 35 nodes 1000 pv h2e2 h9g7", flush=True)
        print("info depth 12 multipv 3 score cp 10 nodes 700 pv c3c4 h9g7", flush=True)
        print("bestmove h2e2 ponder h9g7", flush=True)
    elif command == "quit":
        break

"""Simple HTTP proxy: listens on port 5000, forwards to port 8080"""
import socket
import threading
import sys
import time

TARGET_PORT = 8080
LISTEN_PORT = 5000

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

def handle_client(client_sock):
    try:
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect(('127.0.0.1', TARGET_PORT))
        t1 = threading.Thread(target=forward, args=(client_sock, target), daemon=True)
        t2 = threading.Thread(target=forward, args=(target, client_sock), daemon=True)
        t1.start()
        t2.start()
    except Exception as e:
        client_sock.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', LISTEN_PORT))
    server.listen(100)
    print(f"Proxy listening on :{LISTEN_PORT} -> :{TARGET_PORT}", flush=True)
    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except Exception as e:
            print(f"Accept error: {e}", flush=True)

if __name__ == '__main__':
    main()

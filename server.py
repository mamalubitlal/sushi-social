import socket
import threading
import json
from datetime import datetime

class SushiServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.clients = []

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"New connection from {client_address}")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode()
                if message:
                    data = json.loads(message)
                    if data['type'] == 'heartbeat':
                        self.handle_heartbeat(client_socket)
                    elif data['type'] == 'thread':
                        self.handle_thread(data)
                        self.broadcast(client_socket, message)
            except Exception as e:
                print(f"Error: {e}")
                self.clients.remove(client_socket)
                client_socket.close()
                break

    def handle_heartbeat(self, client_socket):
        print("Heartbeat received")
        client_socket.send(json.dumps({'type': 'heartbeat_ack'}).encode())

    def handle_thread(self, data):
        print(f"New thread from {data['author']}: {data['content']}")
        if data['image']:
            print(f"Image attached: {data['image'][:30]}...")

    def broadcast(self, client_socket, message):
        for client in self.clients:
            if client != client_socket:
                try:
                    client.send(message.encode())
                except:
                    self.clients.remove(client)
                    client.close()

if __name__ == "__main__":
    server = SushiServer()
    server.start()

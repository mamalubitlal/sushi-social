import socket
import json
import base64
import os
from datetime import datetime
from colorama import init, Fore, Back, Style
import threading
import time

init()

class SushiClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.connected = False
        self.threads = []
        self.running = False

    def connect(self, host='localhost', port=5000):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.running = True
            # Start heartbeat thread
            threading.Thread(target=self._heartbeat, daemon=True).start()
            return True
        except Exception as e:
            print(f"{Fore.RED}Connection failed: {e}{Style.RESET_ALL}")
            return False

    def _heartbeat(self):
        while self.running:
            try:
                self.socket.send(json.dumps({'type': 'heartbeat'}).encode())
                time.sleep(5)
            except:
                self.disconnect()
                break

    def login(self, username):
        self.username = username
        self.socket.send(username.encode())

    def post_thread(self, content, image_path=None):
        thread_data = {
            'type': 'thread',
            'content': content,
            'author': self.username,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'image': None
        }
        
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as img:
                thread_data['image'] = base64.b64encode(img.read()).decode()
                
        self.socket.send(json.dumps(thread_data).encode())

    def start_session(self):
        try:
            while self.running:
                print(f"\n{Fore.CYAN}=== Sushi Menu ==={Style.RESET_ALL}")
                print("1. Create Post")
                print("2. View Posts")
                print("3. Logout")
                
                choice = input("> ")
                if not self.connected:
                    print(f"{Fore.RED}Connection lost. Please reconnect.{Style.RESET_ALL}")
                    break

                if choice == "1":
                    content = input("Content: ")
                    image = input("Image path (optional): ")
                    self.post_thread(content, image if image else None)
                elif choice == "2":
                    self.view_threads()
                elif choice == "3":
                    self.disconnect()
                    break
        except Exception as e:
            print(f"{Fore.RED}Session ended: {e}{Style.RESET_ALL}")
        finally:
            self.disconnect()

    def disconnect(self):
        self.running = False
        self.connected = False
        try:
            self.socket.close()
        except:
            pass

class ServerBrowser:
    def __init__(self):
        self.known_servers = self._load_servers()
        
    def _load_servers(self):
        if os.path.exists('servers.json'):
            with open('servers.json', 'r') as f:
                return json.load(f)
        return [
            {"name": "Local", "host": "localhost", "port": 5000},
            {"name": "Default", "host": "127.0.0.1", "port": 5000}
        ]

    def list_servers(self):
        print(f"\n{Fore.CYAN}=== Available Servers ==={Style.RESET_ALL}")
        if not self.known_servers:
            print("No saved servers found.")
            print("0. Connect manually (enter IP)")
            return 0
            
        for i, server in enumerate(self.known_servers):
            status = "🟢 Online" if self.test_server(server["host"], server["port"]) else "🔴 Offline"
            print(f"{i+1}. {server['name']} ({server['host']}:{server['port']}) - {status}")
        print("0. Connect manually (enter IP)")
        return len(self.known_servers)

    def test_server(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def add_server(self, name, host, port):
        self.known_servers.append({"name": name, "host": host, "port": port})
        self.save_servers()

    def save_servers(self):
        with open('servers.json', 'w') as f:
            json.dump(self.known_servers, f)

if __name__ == "__main__":
    print(f"{Fore.CYAN}=== Sushi Social Network Client ==={Style.RESET_ALL}")
    browser = ServerBrowser()
    
    while True:
        print("\n1. Connect to server")
        print("2. Add new server")
        print("3. Exit")
        
        choice = input("> ")
        if choice == "1":
            num_servers = browser.list_servers()
            server_choice = input("Choose server number (0 for manual IP, 'c' to cancel): ")
            
            if server_choice == "0":
                host = input("Enter server IP: ")
                port = int(input("Port (default: 5000): ") or "5000")
                client = SushiClient()
                if client.connect(host, port):
                    username = input("Username: ")
                    client.login(username)
                    client.connected = True
                    client.start_session()
            
        elif choice == "2":
            name = input("Server name: ")
            host = input("Host (IP/domain): ")
            port = int(input("Port (default: 5000): ") or "5000")
            browser.add_server(name, host, port)
            print(f"{Fore.GREEN}Server added successfully!{Style.RESET_ALL}")
            
        elif choice == "3":
            print(f"{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
            break
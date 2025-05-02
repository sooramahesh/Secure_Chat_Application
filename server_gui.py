import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from datetime import datetime
from crypto_utils import encrypt_message, decrypt_message
import json
import hashlib

class ChatServer:
    def __init__(self, master):
        self.master = master
        self.master.title("🔒 Secure Chat - Server")
        self.master.geometry("600x500")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Authenticate user
        if not self.authenticate_user():
            messagebox.showerror("Authentication Failed", "Invalid username or password. Exiting.")
            self.master.destroy()
            return

        # Input username for the server
        self.username = simpledialog.askstring("Username", "Enter your display username:", parent=master)
        if not self.username:
            self.username = "Server"

        # Server status indicator
        self.status_frame = tk.Frame(master)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(self.status_frame, text="Status: Server Stopped", fg="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.server_button = tk.Button(self.status_frame, text="Start Server", command=self.toggle_server)
        self.server_button.pack(side=tk.RIGHT)

        # Chat area
        self.text_area = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=60, height=20, state='disabled')
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Message input area
        self.input_frame = tk.Frame(master)
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.entry = tk.Entry(self.input_frame, width=50)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_message)
        self.entry.config(state=tk.DISABLED)

        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message, state=tk.DISABLED)
        self.send_button.pack(side=tk.RIGHT)

        # Server variables
        self.sock = None
        self.conn = None
        self.addr = None
        self.client_username = None
        self.server_running = False
        self.client_connected = False
        self.accept_thread = None

    def authenticate_user(self):
        """Authenticate user with username and password against users.json"""
        try:
            with open("users.json", "r") as f:
                users_data = json.load(f)
                users = {user["username"]: user["password_hash"] for user in users_data["users"]}
        except FileNotFoundError:
            print("Error: users.json not found.")
            return False

        # Custom authentication dialog
        auth_dialog = tk.Toplevel(self.master)
        auth_dialog.title("Login")
        auth_dialog.geometry("300x150")
        auth_dialog.transient(self.master)
        auth_dialog.grab_set()

        tk.Label(auth_dialog, text="Username:").pack(pady=5)
        username_entry = tk.Entry(auth_dialog)
        username_entry.pack(pady=5)
        tk.Label(auth_dialog, text="Password:").pack(pady=5)
        password_entry = tk.Entry(auth_dialog, show="*")
        password_entry.pack(pady=5)

        result = {"authenticated": False}

        def verify():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if username in users:
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                if input_hash == users[username]:
                    result["authenticated"] = True
            auth_dialog.destroy()

        tk.Button(auth_dialog, text="Login", command=verify).pack(pady=10)
        self.master.wait_window(auth_dialog)
        return result["authenticated"]

    def toggle_server(self):
        if not self.server_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        try:
            # Setup socket connection
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('localhost', 12345))
            self.sock.listen(1)
            self.server_running = True
            
            # Update UI
            self.status_label.config(text="Status: Waiting for connection", fg="orange")
            self.server_button.config(text="Stop Server")
            
            self.log_message("Server started. Waiting for connection...", message_type="system")
            
            # Start thread to accept connections
            self.accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.accept_thread.start()
            
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
            self.stop_server()

    def stop_server(self):
        # Disconnect client if connected
        if self.client_connected:
            self.disconnect_client()
            
        # Close server socket
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
                
        # Update UI and status
        self.server_running = False
        self.status_label.config(text="Status: Server Stopped", fg="red")
        self.server_button.config(text="Start Server")
        self.entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        
        self.log_message("Server stopped", message_type="system")

    def accept_connections(self):
        while self.server_running:
            try:
                # Set a timeout so we can check if server is still running
                self.sock.settimeout(1.0)
                try:
                    self.conn, self.addr = self.sock.accept()
                except socket.timeout:
                    continue
                    
                # Reset timeout
                self.sock.settimeout(None)
                
                # Get client username
                self.client_username = self.conn.recv(1024).decode()
                
                # Send server username
                self.conn.send(self.username.encode())
                
                # Update UI
                self.client_connected = True
                self.status_label.config(text=f"Connected to: {self.client_username}", fg="green")
                self.entry.config(state=tk.NORMAL)
                self.send_button.config(state=tk.NORMAL)
                
                self.log_message(f"Client connected: {self.client_username} from {self.addr}", message_type="system")
                
                # Start receiving messages
                receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
                receive_thread.start()
                
                # Wait until client disconnects before accepting new connections
                receive_thread.join()
                
            except Exception as e:
                if self.server_running:  # Only log if server is still running
                    self.log_message(f"Error in connection: {str(e)}", message_type="error")
            
            finally:
                self.disconnect_client()

    def disconnect_client(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
                
        self.client_connected = False
        self.conn = None
        self.client_username = None
        
        # Update UI
        if self.server_running:
            self.status_label.config(text="Status: Waiting for connection", fg="orange")
        self.entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        
        if self.server_running:
            self.log_message("Client disconnected. Waiting for new connection.", message_type="system")

    def send_message(self, event=None):
        message = self.entry.get().strip()
        if message and self.client_connected:
            try:
                encrypted = encrypt_message(message)
                self.conn.send(encrypted)

                self.log_message(message, sender=self.username)
                self.entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Failed to send message: {str(e)}", message_type="error")
                self.disconnect_client()

    def receive_messages(self):
        while self.client_connected:
            try:
                data = self.conn.recv(1024)
                if not data:
                    # Client has disconnected
                    break
                    
                decrypted = decrypt_message(data)
                self.log_message(decrypted, sender=self.client_username)
                
            except ConnectionResetError:
                self.log_message("Connection was reset by the client", message_type="error")
                break
            except Exception as e:
                self.log_message(f"Error receiving message: {str(e)}", message_type="error")
                break

    def log_message(self, message, sender=None, message_type="normal"):
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Use after to update from any thread
        self.master.after(0, self._update_text_area, message, sender, timestamp, message_type)

    def _update_text_area(self, message, sender, timestamp, message_type):
        self.text_area.config(state='normal')
        
        if message_type == "error":
            self.text_area.insert(tk.END, f"[ERROR] ({timestamp}): {message}\n", "error")
            self.text_area.tag_configure("error", foreground="red")
        elif message_type == "system":
            self.text_area.insert(tk.END, f"[SYSTEM] ({timestamp}): {message}\n", "system")
            self.text_area.tag_configure("system", foreground="blue")
        else:
            if sender:
                self.text_area.insert(tk.END, f"{sender} ({timestamp}): ", "sender")
                self.text_area.tag_configure("sender", foreground="green")
                self.text_area.insert(tk.END, f"{message}\n")
            else:
                self.text_area.insert(tk.END, f"({timestamp}): {message}\n")
                
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def on_closing(self):
        self.stop_server()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatServer(root)
    root.mainloop()
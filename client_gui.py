import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from datetime import datetime
from crypto_utils import encrypt_message, decrypt_message
import json
import os
import sys
import hashlib

class ChatClient:
    def __init__(self, master, auto_connect=False):
        self.master = master
        self.master.title("🔐 Secure Chat - Client")
        self.master.geometry("600x500")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Authenticate user
        if not self.authenticate_user():
            messagebox.showerror("Authentication Failed", "Invalid username or password. Exiting.")
            self.master.destroy()
            return

        # Chat history
        self.chat_history = []
        self.history_file = "chat_history.json"
        self.load_chat_history()

        # Input username for the client
        self.username = simpledialog.askstring("Username", "Enter your display username:", parent=master)
        if not self.username:
            self.username = "Client"

        # Connection status indicator
        self.status_frame = tk.Frame(master)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(self.status_frame, text="Status: Disconnected", fg="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.connection_button = tk.Button(self.status_frame, text="Connect", command=self.connect_to_server)
        self.connection_button.pack(side=tk.RIGHT)
        
        self.new_client_button = tk.Button(self.status_frame, text="New Client", command=self.new_client, state=tk.DISABLED)
        self.new_client_button.pack(side=tk.RIGHT, padx=5)

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

        self.sock = None
        self.server_username = None
        self.connected = False
        
        # Display previous chat history
        self.display_chat_history()
        
        # Auto-connect if requested
        if auto_connect:
            self.master.after(100, self.connect_to_server)

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

    def load_chat_history(self):
        """Load chat history from file if it exists"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.chat_history = json.load(f)
        except Exception as e:
            print(f"Error loading chat history: {e}")
            self.chat_history = []

    def save_chat_history(self):
        """Save chat history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.chat_history, f)
        except Exception as e:
            print(f"Error saving chat history: {e}")

    def display_chat_history(self):
        """Display the loaded chat history in the text area"""
        if not self.chat_history:
            return
            
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, "--- Chat History ---\n", "history_header")
        self.text_area.tag_configure("history_header", foreground="purple")
        
        for entry in self.chat_history:
            timestamp = entry.get('timestamp', '')
            message = entry.get('message', '')
            sender = entry.get('sender', '')
            message_type = entry.get('type', 'normal')
            
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
        
        self.text_area.insert(tk.END, "--- End of History ---\n\n", "history_footer")
        self.text_area.tag_configure("history_footer", foreground="purple")
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def connect_to_server(self):
        if self.connected:
            return
            
        # Connect to server
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', 12345))
            self.connected = True
            
            # Send username to server
            self.sock.send(self.username.encode())
            
            # Receive the server's username
            self.server_username = self.sock.recv(1024).decode()
            
            # Update UI
            self.status_label.config(text=f"Connected to: {self.server_username}", fg="green")
            self.connection_button.config(text="Disconnect", command=self.disconnect_from_server)
            self.new_client_button.config(state=tk.DISABLED)
            self.entry.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)
            
            # Log the connection
            self.log_message(f"Connected to {self.server_username}!", message_type="system")
            
            # Start receiving messages
            threading.Thread(target=self.receive_messages, daemon=True).start()

        except ConnectionRefusedError:
            messagebox.showerror("Error", "Could not connect to the server.")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")

    def disconnect_from_server(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
                
        self.connected = False
        self.status_label.config(text="Status: Disconnected", fg="red")
        self.connection_button.config(text="Connect", command=self.connect_to_server)
        self.new_client_button.config(state=tk.NORMAL)
        self.entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.log_message("Disconnected from server", message_type="system")
        
        # Save chat history when disconnecting
        self.save_chat_history()

    def new_client(self):
        """Launch a new client instance"""
        self.save_chat_history()
        
        # Create a Python command to restart the program
        python = sys.executable
        os.execl(python, python, *sys.argv, "--auto-connect")

    def send_message(self, event=None):
        message = self.entry.get().strip()
        if message and self.connected:
            try:
                encrypted = encrypt_message(message)
                self.sock.send(encrypted)

                self.log_message(message, sender=self.username)
                self.entry.delete(0, tk.END)
            except Exception as e:
                self.log_message(f"Failed to send message: {str(e)}", message_type="error")
                self.disconnect_from_server()

    def receive_messages(self):
        while self.connected:
            try:
                data = self.sock.recv(1024)
                if not data:
                    # Server disconnected
                    break
                    
                decrypted = decrypt_message(data)
                self.log_message(decrypted, sender=self.server_username)
                
            except ConnectionResetError:
                self.log_message("Connection was reset by the server", message_type="error")
                break
            except Exception as e:
                self.log_message(f"Error receiving message: {str(e)}", message_type="error")
                break
                
        # If we exit the loop, we're disconnected
        if self.connected:  # Only update if we haven't manually disconnected
            self.master.after(100, self.disconnect_from_server)

    def log_message(self, message, sender=None, message_type="normal"):
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Add to chat history
        history_entry = {
            'timestamp': timestamp,
            'message': message,
            'sender': sender,
            'type': message_type
        }
        self.chat_history.append(history_entry)
        
        # Update text area
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
        self.disconnect_from_server()
        self.save_chat_history()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Check if auto-connect flag is present
    auto_connect = "--auto-connect" in sys.argv
    app = ChatClient(root, auto_connect)
    root.mainloop()

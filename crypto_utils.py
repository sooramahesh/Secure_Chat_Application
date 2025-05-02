from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import os
import base64

# In a real application, this should be generated securely and exchanged
# using a key exchange protocol like Diffie-Hellman
KEY = b'Sixteen byte key'  # 16-byte (128-bit) secret key

def encrypt_message(message):
    """
    Encrypts a message using AES-CBC with PKCS7 padding
    Returns IV + encrypted data
    """
    iv = os.urandom(16)  # Generate a random 16-byte initialization vector
    
    # Pad the message to be a multiple of the block size (16 bytes for AES)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(message.encode('utf-8')) + padder.finalize()
    
    # Create the cipher with AES algorithm in CBC mode
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Encrypt the padded data
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    
    # Return IV + ciphertext
    return iv + encrypted

def decrypt_message(ciphertext):
    """
    Decrypts a message using AES-CBC with PKCS7 padding
    Expects IV + encrypted data format
    """
    try:
        # Extract the IV from the first 16 bytes
        iv = ciphertext[:16]
        actual_cipher = ciphertext[16:]
        
        # Create the cipher with AES algorithm in CBC mode
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # Decrypt the ciphertext
        decrypted_padded = decryptor.update(actual_cipher) + decryptor.finalize()
        
        # Remove the padding
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted.decode('utf-8')
    except Exception as e:
        return f"[Decryption Error: {str(e)}]"
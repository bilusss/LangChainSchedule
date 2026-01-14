#!/usr/bin/env python3
"""Generate PNG assets for Expo app"""
import struct
import zlib
import os

def create_png(width, height, r, g, b, filename):
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = zlib.crc32(chunk) & 0xffffffff
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', crc)
    
    # PNG signature
    png = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    png += make_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (image data)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter type none
        raw_data += bytes([r, g, b] * width)
    
    compressed = zlib.compress(raw_data, 9)
    png += make_chunk(b'IDAT', compressed)
    
    # IEND chunk
    png += make_chunk(b'IEND', b'')
    
    with open(filename, 'wb') as f:
        f.write(png)
    print(f"Created: {filename}")

if __name__ == "__main__":
    assets_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(assets_dir)
    
    # Dark purple background (#1a1a2e = 26, 26, 46)
    create_png(1024, 1024, 26, 26, 46, 'icon.png')
    create_png(1024, 1024, 26, 26, 46, 'adaptive-icon.png')
    create_png(2048, 1024, 26, 26, 46, 'splash.png')
    create_png(48, 48, 26, 26, 46, 'favicon.png')

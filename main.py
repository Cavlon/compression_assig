import os
import chardet
from charset_normalizer import from_path

## IDEAS
# Fix the size of the dictionary to be a certain bit length (ensure each taken takes a fixed number of bits), keep track of the least recently used index and replace it when a new entry is added if the dictionary is full

# Takes a file to encode, compresses it via LZW, and saves the result as a binary file
def encode(encode_file, result_file):
    
    # Check if file exists
    if not os.path.exists(encode_file):
        print("File not found")
        return

    f = open(encode_file, 'rb')

    print(f"\nEncoding file: {encode_file}")
    print(f"File Size: {os.path.getsize(encode_file)} bytes\n")
    
    # Initialise the dictionary with 256 bytes
    dictionary = {bytes([i]): i for i in range(256)}
    next_index = 256
    encode_string = b''

    encode_bits = 9
    bit_buffer = 0  # Holds encoded bits
    buffer_size = 0 # The number of relevant bits in the buffer
    
    with open(result_file, 'wb') as cf:
        # Encode the contents
        while True:
            # Process the next byte
            next_char = f.read(1)

            # End of file
            if not next_char:
                break
            
            encode_string += next_char

            if encode_string not in dictionary:
                # Write the token to the compressed file
                # Add token bits to the buffer
                bit_buffer = (bit_buffer << encode_bits) | dictionary[encode_string[:-1]]
                buffer_size += encode_bits

                # While there are enough bits to form a byte
                while buffer_size >= 8:
                    # Write the leftmost byte to the file
                    buffer_size -= 8
                    cf.write(bytes([bit_buffer >> buffer_size]))
                    bit_buffer &= ((1 << buffer_size) - 1)

                dictionary[encode_string] = next_index

                encode_string = next_char
                next_index += 1

                # Assign more token bits if dictionary is too large
                if next_index >= (1 << encode_bits):
                    encode_bits += 1
        
        # Write the leftover string
        if encode_string:
            bit_buffer = (bit_buffer << encode_bits) | dictionary[encode_string]
            buffer_size += encode_bits

            while buffer_size >= 8:
                buffer_size -= 8
                cf.write(bytes([bit_buffer >> buffer_size]))
                bit_buffer &= ((1 << buffer_size) - 1)
            
            # Pad the final bits to form a byte
            if buffer_size > 0:
                cf.write(bytes([(bit_buffer << (8 - buffer_size))]))
    
    f.close()

    print(f"Encoded File Size: {os.path.getsize(result_file)} bytes\n")

# Takes a compressed binary file to decode, decompresses it via LZW, and saves the result
def decode(compressed_file, result_file):

    # Check if file exists
    if not os.path.exists(compressed_file):
        print("File not found")
        return

    f = open(compressed_file, 'rb')

    print(f"\nCompressed File: {compressed_file}")
    print(f"Compressed File Size: {os.path.getsize(compressed_file)} bytes\n")

    # Initialise the dictionary with 256 bytes
    dictionary = [bytes([i]) for i in range(256)]
    length = 256

    encode_bits = 9
    bit_buffer = 0  # Holds encoded bits
    buffer_size = 0 # The number of relevant bits in the buffer

    # Read bytes until there are enough bits to form a token
    while buffer_size < encode_bits:
        bit_buffer = (bit_buffer << 8) | f.read(1)[0]
        buffer_size += 8
    
    # Extract the first token from the buffer
    buffer_size -= encode_bits
    next_token = (bit_buffer >> buffer_size)
    bit_buffer &= ((1 << buffer_size) - 1)
    prev_string = dictionary[next_token]

    with open(result_file, 'wb') as rf:

        # Write the first decoded string
        rf.write(prev_string)
        eof = False

        while True:
            # Process the next token
            # Read bytes until there are enough bits to form a token
            while buffer_size < encode_bits:
                byte = f.read(1)

                # End of file
                if not byte:
                    eof = True
                    break

                bit_buffer = (bit_buffer << 8) | byte[0]
                buffer_size += 8

            # Extract the next token if possible
            if buffer_size >= encode_bits:
                buffer_size -= encode_bits
                next_token = (bit_buffer >> buffer_size)
                bit_buffer &= ((1 << buffer_size) - 1)

            elif eof:
                break

            if next_token < length: # String matches an entry from before t-1
                decoded_string = dictionary[next_token]
            else:                   # String matches the t-1th entry
                decoded_string = prev_string + prev_string[:1]
        
            # Write the decoded string to the output file
            rf.write(decoded_string)
            dictionary.append(prev_string + decoded_string[:1])
            prev_string = decoded_string
            length += 1
            
            # Sync up when token bits would increase (decompressor is 1 step behind so it needs to check next length)
            if length + 1 >= (1 << encode_bits):
                    encode_bits += 1
    
    f.close()

    print(f"File Size: {os.path.getsize(result_file)} bytes\n")

def main():
    while True:
        command = input("Enter a command (print, encode, decode, or exit): ").lower()

        # Open and print file
        if command == "print":
            file_path = input("Enter file path to open and print: ")

            # Check if the file exists
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    print(f"\nReading text file: {file_path}")
                    print(f"File Size: {os.path.getsize(file_path)} bytes")
                    print(f"Content Length: {len(content)}")
                    print(f"Encoding: {from_path(file_path).best().encoding}\n")
                    print(content[:200])

                except Exception as e:
                    # It's a binary file
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        print(f"\nReading binary file: {file_path}")
                        print(f"File Size: {os.path.getsize(file_path)} bytes")
                        print(f"Content Length: {len(content)}")
                        print(f"Encoding: {chardet.detect(content)['encoding']}\n")
                        print(content[:200])

                    except Exception as e2:
                        print("Error reading file")

            else:
                print("File not found")
        
        # Compress file and save it
        elif command == "encode":
            file_path = input("Enter file path to encode: ")
            result_file = input("Enter name of resultant encoded file: ")
            encode(file_path, result_file)
        
        # Decompress file and save it
        elif command == "decode":
            file_path = input("Enter file path to decode: ")
            result_file = input("Enter name of resultant decoded file: ")
            decode(file_path, result_file)
        
        elif command == "test":
            print(bin((0 << 10) | 50))
            
        elif command == "exit":
            return

        else:
            print("Invalid command")


if __name__ == "__main__":
    main()
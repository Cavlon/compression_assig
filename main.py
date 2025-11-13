import os
import heapq
from collections import OrderedDict

## IDEAS
# Add empty file handling

# Encodes a file with LZW/LRU
def encode_lru(encode_file, result_file, max_bits = 16):
    
    # Check if file exists
    if not os.path.exists(encode_file):
        print("File not found")
        return

    f = open(encode_file, 'rb')

    print(f"\nEncoding file: {encode_file}")
    print(f"File Size: {os.path.getsize(encode_file)} bytes\n")

    # Initialise the dictionary with 256 bytes
    fixed_dictionary = {bytes([i]): i for i in range(256)}
    dictionary = OrderedDict()

    full = False
    next_index = 256
    encode_string = f.read(1)

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

                match_string = encode_string[:-1]
                if len(match_string) == 1:
                    match_index = fixed_dictionary[match_string]
                else:
                    match_index = dictionary[match_string]
                
                # Update the recency of all prefixes of the matched string
                if len(match_string) > 1:
                    for i in range(2, len(match_string)):
                        dictionary.move_to_end(match_string[:i])

                # Add token bits to the buffer
                bit_buffer = (bit_buffer << encode_bits) | match_index
                buffer_size += encode_bits

                # While there are enough bits to form a byte
                while buffer_size >= 8:
                    # Write the leftmost byte to the file
                    buffer_size -= 8
                    cf.write(bytes([bit_buffer >> buffer_size]))
                    bit_buffer &= ((1 << buffer_size) - 1)

                if full:    # Dictionary is full
                    oldest_string, next_index = dictionary.popitem(last=False)
                    dictionary[encode_string] = next_index
                
                else:
                    dictionary[encode_string] = next_index
                    next_index += 1

                    # Assign more token bits if dictionary is too large
                    if next_index >= (1 << encode_bits):
                        if encode_bits == max_bits:
                            full = True
                        else:
                            encode_bits += 1
                
                encode_string = next_char
        
        # Write the leftover string
        if encode_string:

            if len(encode_string) == 1:
                match_index = fixed_dictionary[encode_string]
            else:
                match_index = dictionary[encode_string]

            bit_buffer = (bit_buffer << encode_bits) | match_index
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

# Decodes a LZW/LRU encoded file
def decode_lru(compressed_file, result_file, max_bits = 16):

    # Check if file exists
    if not os.path.exists(compressed_file):
        print("File not found")
        return

    f = open(compressed_file, 'rb')

    print(f"\nCompressed File: {compressed_file}")
    print(f"Compressed File Size: {os.path.getsize(compressed_file)} bytes\n")

    # Initialise the dictionary with 256 bytes
    dictionary_map = OrderedDict()
    dictionary = [bytes([i]) for i in range(256)]

    next_index = 256
    full = False

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

        while True:
            # Process the next token
            # Read bytes until there are enough bits to form a token
            while buffer_size < encode_bits:
                byte = f.read(1)

                # End of file
                if not byte:
                    break

                bit_buffer = (bit_buffer << 8) | byte[0]
                buffer_size += 8

            # Extract the next token if possible
            if buffer_size >= encode_bits:
                buffer_size -= encode_bits
                next_token = (bit_buffer >> buffer_size)
                bit_buffer &= ((1 << buffer_size) - 1)
            else:
                break

            if full:    # Dictionary is full
                if next_token == next_index:    # String matches the t-1th entry
                    decoded_string = prev_string + prev_string[:1]
                else:                           # String matches an entry from before t-1
                    decoded_string = dictionary[next_token]
                
                new_entry = prev_string + decoded_string[:1]

                dictionary[next_index] = new_entry
                dictionary_map[new_entry] = next_index

            else:

                if next_token < next_index: # String matches an entry from before t-1
                    decoded_string = dictionary[next_token]
                else:                       # String matches the t-1th entry
                    decoded_string = prev_string + prev_string[:1]

                new_entry = prev_string + decoded_string[:1]

                dictionary.append(new_entry)
                dictionary_map[new_entry] = next_index

                next_index += 1

                # Sync up when token bits would increase (decoder is 1 step behind so it needs to check next_index+1)
                if next_index + 1 >= (1 << encode_bits):
                    if encode_bits < max_bits: 
                        encode_bits += 1

                    # The dictionary is full
                    elif next_index == (1 << max_bits):
                        full = True

            # Update the recency of all prefixes of the matched string
            if len(decoded_string) > 1:
                for i in range(2, len(decoded_string)):
                    dictionary_map.move_to_end(decoded_string[:i])
            
            # An entry should have been replaced at this timestep in the encoder
            if full:
                oldest_string, next_index = dictionary_map.popitem(last=False)
        
            # Write the decoded string to the output file
            rf.write(decoded_string)                
            prev_string = decoded_string
    
    f.close()

    print(f"File Size: {os.path.getsize(result_file)} bytes\n")

# Encodes a file with LZW/Aging
def encode_ttl(encode_file, result_file, max_bits = 16):
    
    # Check if file exists
    if not os.path.exists(encode_file):
        print("File not found")
        return

    f = open(encode_file, 'rb')

    print(f"\nEncoding file: {encode_file}")
    print(f"File Size: {os.path.getsize(encode_file)} bytes\n")
    
    # Keeps track of the lowest ttl
    min_heap = []
    # All indices freed via ttl deletion
    freed_indices = []

    # Initialise the dictionary with 256 bytes
    dictionary = {bytes([i]): i for i in range(256)}

    full = False
    next_index = 256
    encode_string = b''

    encode_bits = 9
    bit_buffer = 0  # Holds encoded bits
    buffer_size = 0 # The number of relevant bits in the buffer

    t = 0
    init_ttl = (1 << max_bits) // 1024
    
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

                match_string = encode_string[:-1]
                if len(match_string) == 1:
                    match_index = dictionary[match_string]
                else:
                    match_index = dictionary[match_string][0]

                # Add token bits to the buffer
                bit_buffer = (bit_buffer << encode_bits) | match_index
                buffer_size += encode_bits

                # While there are enough bits to form a byte
                while buffer_size >= 8:
                    # Write the leftmost byte to the file
                    buffer_size -= 8
                    cf.write(bytes([bit_buffer >> buffer_size]))
                    bit_buffer &= ((1 << buffer_size) - 1)

                if full:    # Dictionary is full
                    if freed_indices:   # Use a free index to write the new entry
                        dictionary[encode_string] = [freed_indices.pop(1), init_ttl]
                        heapq.heappush(min_heap, (init_ttl, encode_string))
                    else:               # Replace the entry with the lowest ttl
                        ttl, oldest_string = heapq.heapreplace(min_heap, (init_ttl, encode_string))

                        next_index = dictionary[oldest_string][0]
                        del dictionary[oldest_string]
                        dictionary[encode_string] = [next_index, init_ttl]
                
                else:
                    dictionary[encode_string] = [next_index, init_ttl]
                    next_index += 1

                    heapq.heappush(min_heap, (init_ttl, encode_string))

                    # Assign more token bits if dictionary is too large
                    if next_index >= (1 << encode_bits):
                        if encode_bits == max_bits:
                            full = True
                        else:
                            encode_bits += 1

                # All entries 1 character entries should stay fixed
                if len(match_string) > 1:
                    # Update the ttl of the matched entry
                    ttl = dictionary[match_string][1]
                    heap_index = min_heap.index((ttl, match_string))

                    ttl = ttl // 2 + init_ttl
                    dictionary[match_string][1] = ttl

                    min_heap[heap_index] = (ttl, match_string)
                    heapq._siftup(min_heap, heap_index)

                t += 1

                # Decrement the ttls of all entries at fixed timesteps
                if t % 1024 == 0:
                    for i, (ttl, string) in enumerate(min_heap):
                        if string == encode_string: # The decoder doesn't know the string added at this timestep so don't consider it
                            continue
                        ttl -= 1
                        if ttl == 0:    # Delete dead entries and free their indices
                            min_heap[i] = min_heap[-1]
                            min_heap.pop()
                            freed_indices.append(dictionary[string][0])
                            del dictionary[string]
                            continue

                        min_heap[i] = (ttl, string)
                        dictionary[string][1] -= 1
                    
                    heapq.heapify(min_heap)
                
                encode_string = next_char
        
        # Write the leftover string
        if encode_string:

            if len(encode_string) == 1:
                match_index = dictionary[encode_string]
            else:
                match_index = dictionary[encode_string][0]

            bit_buffer = (bit_buffer << encode_bits) | match_index
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

# Decodes a LZW/Aging encoded file
def decode_ttl(compressed_file, result_file, max_bits = 16):

    # Check if file exists
    if not os.path.exists(compressed_file):
        print("File not found")
        return

    f = open(compressed_file, 'rb')

    print(f"\nCompressed File: {compressed_file}")
    print(f"Compressed File Size: {os.path.getsize(compressed_file)} bytes\n")

    # Keeps track of the lowest ttl
    min_heap = []
    # All indices freed via ttl deletion
    freed_indices = []

    # Initialise the dictionary with 256 bytes
    dictionary = [bytes([i]) for i in range(256)]
    string_map = {bytes([i]): i for i in range(256)}

    next_index = 256
    t = 1   # t=1 because decoder parses first token before the loop
    full = False
    init_ttl = (1 << max_bits) // 1024

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

        while True:
            # Process the next token
            # Read bytes until there are enough bits to form a token
            while buffer_size < encode_bits:
                byte = f.read(1)

                # End of file
                if not byte:
                    break

                bit_buffer = (bit_buffer << 8) | byte[0]
                buffer_size += 8

            # Extract the next token if possible
            if buffer_size >= encode_bits:
                buffer_size -= encode_bits
                next_token = (bit_buffer >> buffer_size)
                bit_buffer &= ((1 << buffer_size) - 1)
            else:
                break

            if full:    # Dictionary is full
                if next_token == next_index:    # String matches the t-1th entry
                    decoded_string = prev_string + prev_string[:1]
                else:                           # String matches an entry from before t-1
                    decoded_string = dictionary[next_token]
                
                new_entry = prev_string + decoded_string[:1]

                dictionary[next_index] = new_entry
                string_map[new_entry] = [next_index, init_ttl]
                heapq.heappush(min_heap, (init_ttl, new_entry))

                # Determine the index that was logically replaced this timestep
                if freed_indices:
                    next_index = freed_indices.pop(0)
                else:
                    ttl, string = heapq.heappop(min_heap)
                    next_index = string_map[string][0]
                    del string_map[string]

            else:

                if next_token < next_index: # String matches an entry from before t-1
                    decoded_string = dictionary[next_token]
                else:                       # String matches the t-1th entry
                    decoded_string = prev_string + prev_string[:1]

                new_entry = prev_string + decoded_string[:1]

                dictionary.append(new_entry)
                string_map[new_entry] = [next_index, init_ttl]
                heapq.heappush(min_heap, (init_ttl, new_entry))

                next_index += 1

                # Sync up when token bits would increase (decoder is 1 step behind so it needs to check next_index+1)
                if next_index + 1 >= (1 << encode_bits):
                    if encode_bits < max_bits: 
                        encode_bits += 1

                    # The dictionary is full
                    elif next_index == (1 << max_bits):
                        # There should be a logical entry added this step so the corresponding replacement entry should be purged
                        if freed_indices:
                            next_index = freed_indices.pop(0)
                        else:
                            ttl, string = heapq.heappop(min_heap)
                            next_index = string_map[string][0]
                            del string_map[string]
                        full = True
            
            # All entries 1 character entries should stay fixed
            if next_token > 255:
                # Update the ttl of the matched entry
                entry = string_map[decoded_string]

                ttl = entry[1]
                heap_index = min_heap.index((ttl, decoded_string))

                ttl = ttl // 2 + init_ttl
                entry[1] = ttl

                min_heap[heap_index] = (ttl, decoded_string)
                heapq._siftup(min_heap, heap_index)
            
            t += 1

            # Decrement the ttls of all entries at fixed timesteps
            if t % 1024 == 0:
                for i, (ttl, string) in enumerate(min_heap):
                    ttl -= 1

                    if ttl == 0:    # Delete dead entries and free their indices
                        min_heap[i] = min_heap[-1]
                        min_heap.pop()
                        freed_indices.append(string_map[string][0])
                        del string_map[string]
                        continue

                    min_heap[i] = (ttl, string)
                    string_map[string][1] -= 1
                
                heapq.heapify(min_heap)
        
            # Write the decoded string to the output file
            rf.write(decoded_string)                
            prev_string = decoded_string
    
    f.close()

    print(f"File Size: {os.path.getsize(result_file)} bytes\n")

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
        command = input("Enter a command (print, compare, encode, decode, e+d, or exit): ").lower()

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
                    print(content[:200])

                except Exception as e:
                    # It's a binary file
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        print(f"\nReading binary file: {file_path}")
                        print(f"File Size: {os.path.getsize(file_path)} bytes")
                        print(f"Content Length: {len(content)}")
                        print(content[:200])

                    except Exception as e2:
                        print("Error reading file")

            else:
                print("File not found")
        
        # Compare 2 files to see if the contents match
        elif command == "compare":
            file_path1 = input("Enter 1st file path to compare: ")
            file_path2 = input("Enter 2nd file path to compare: ")

            # Check if the files exist
            if os.path.exists(file_path1) and os.path.exists(file_path2):
                try:
                    with open(file_path1, 'rb') as f1, open(file_path2, 'rb') as f2:
                        same = True

                        # Check each byte matches
                        while True:
                            byte1 = f1.read(1)
                            byte2 = f2.read(1)

                            if not byte1 or not byte2:
                                if byte1 or byte2:
                                    same = False
                                break

                            if byte1 != byte2:
                                same = False
                                break
                        
                        print(f"Files are the same = {same}")

                except Exception as e:
                    print("Error reading file")
            else:
                print("File not found")

        # Compress file and save it
        elif command == "encode":
            file_path = input("Enter file path to encode: ")
            result_file = input("Enter name of resultant encoded file: ")
            method = int(input("Encoding Method 1, 2, or 3? "))
            if method != 1:
                max_bits = int(input("Max Token Bits? "))

            if os.path.isfile(file_path) == True:
                if method == 1:
                    encode(file_path, result_file)
                elif method == 2:   
                    encode_ttl(file_path, result_file, max_bits)
                else:
                    encode_lru(file_path, result_file, max_bits)
            else:
                # Encode all files in a directory
                for file in os.listdir(file_path):
                    if method == 1:
                        encode(file_path + "/" + file, result_file + "/" + file + ".lzw")
                    elif method == 2:   
                        encode_ttl(file_path + "/" + file, result_file + "/" + file + ".lzw", max_bits)
                    else:
                        encode_lru(file_path + "/" + file, result_file + "/" + file + ".lzw", max_bits)
        
        # Decompress file and save it
        elif command == "decode":
            file_path = input("Enter file path to decode: ")
            result_file = input("Enter name of resultant decoded file: ")
            method = int(input("Decoding Method 1, 2, or 3? "))
            if method != 1:
                max_bits = int(input("Max Token Bits? "))

            if os.path.isfile(file_path) == True:
                if method == 1:
                    decode(file_path, result_file)
                elif method == 2:   
                    decode_ttl(file_path, result_file, max_bits)
                else:
                    decode_lru(file_path, result_file, max_bits)
            else:
                # Decode all files in a directory
                for file in os.listdir(file_path):
                    if method == 1:
                        decode(file_path + "/" + file, result_file + "/" + file[:-4])
                    elif method == 2:   
                        decode_ttl(file_path + "/" + file, result_file + "/" + file[:-4], max_bits)
                    else:
                        decode_lru(file_path + "/" + file, result_file + "/" + file[:-4], max_bits)
        
        # Encode then decode
        elif command == "e+d":
            file_path = input("Enter file path to process: ")
            inter_path = input("Enter file path for encoded file: ")
            result_file = input("Enter name of resultant file: ")
            method = int(input("Method 1, 2, or 3? "))
            if method != 1:
                max_bits = int(input("Max Token Bits? "))

            if os.path.isfile(file_path) == True:
                if method == 1:
                    encode(file_path, inter_path)
                    decode(inter_path, result_file)
                elif method == 2:   
                    encode_ttl(file_path, inter_path, max_bits)
                    decode_ttl(inter_path, result_file, max_bits)
                else:
                    encode_lru(file_path, inter_path, max_bits)
                    decode_lru(inter_path, result_file, max_bits)
            else:
                # Encode and decode all files in a directory
                for file in os.listdir(file_path):
                    if method == 1:
                        encode(file_path + "/" + file, inter_path + "/" + file + ".lzw")
                        decode(inter_path + "/" + file + ".lzw", result_file + "/" + file)
                    elif method == 2:   
                        encode_ttl(file_path + "/" + file, inter_path + "/" + file + ".lzw", max_bits)
                        decode_ttl(inter_path + "/" + file + ".lzw", result_file + "/" + file, max_bits)
                    else:
                        encode_lru(file_path + "/" + file, inter_path + "/" + file + ".lzw", max_bits)
                        decode_lru(inter_path + "/" + file + ".lzw", result_file + "/" + file, max_bits)
            
        elif command == "exit":
            return

        else:
            print("Invalid command")


if __name__ == "__main__":
    main()
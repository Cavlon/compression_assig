import os

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
                        content = f.read(200)
                    print(f"Reading text file: {os.path.getsize(file_path)} bytes")
                    print(content)

                except Exception as e:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read(200)
                        print(f"Reading binary file: {os.path.getsize(file_path)} bytes")
                        print(content)

                    except Exception as e2:
                        print("Error reading file")

            else:
                print("File not found")

        elif command == "exit":
            return

        else:
            print("Invalid command")


if __name__ == "__main__":
    main()
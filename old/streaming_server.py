import socketserver
import threading
import time
import logging
import os
import data_generation

def start_server_thread():
    class MySocketHandler(socketserver.BaseRequestHandler):
        def handle(self):
            for staged_file in os.listdir("tmp/staged"):
                with open(staged_file, "r") as file_to_send:
                    for line in file_to_send:
                        self.request.sendall(line.encode("UTF-8"))
                        time.sleep(0.1)

            self.request.close()
    logging.info("Thread starting")
    socketserver.TCPServer(("127.0.0.1", 9999),MySocketHandler).serve_forever()
    logging.info("Thread finishing")


if __name__ == "__main__":
    # data_generation.run()
    
    thread = threading.Thread(target=start_server_thread, daemon=True)
    thread.start()
    thread.join(100)

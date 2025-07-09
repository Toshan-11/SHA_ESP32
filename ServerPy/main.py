import socket
from typing import Literal

HOST = "192.168.137.24"
PORT = 1234


def read_from_server(s):
    c=""
    while "\n" not in c:
        c += s.recv(1).decode()
    return c


def init_esp():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Connecting to server....{(HOST, PORT)=}")
    s.connect((HOST, PORT))
    print("Sucessfully connected to esp")
    return s 

def pin_state(s:socket,pin:int,state:Literal[1,0]):
    if state not in [1,0]:
        raise ValueError("Invalid state")
    message = f"{pin} {state}\n".encode()
    print(f"Sending.... {message}")
    s.sendall(message)
    data = read_from_server(s)
    print("ESP32 Response: ",data)




def cli_mainloop():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print(f"Connecting to server....{(HOST, PORT)=}")
        s.connect((HOST, PORT))
        while True:
            print("*"*10)
            pin,state,*_=checker = input("Enter pin and state as pin,state\n").strip().split(",")
            if(len(checker)!=2):
                print(f"Error invalid input {checker=}")
                continue
            pin_state(s,pin,state)
            
            


# cli_mainloop()
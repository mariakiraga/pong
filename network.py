import socket
import pickle
import struct

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = 
        self.port = 5555
        self.addr = (self.server, self.port)
        self.p = self.connect()

    def getP(self):
        return self.p

    def send_msg(self, sock, msg):
        # Pakuje długość wiadomości (4 bajty) i dokleja do niej właściwe dane
        msg = struct.pack('>I', len(msg)) + msg
        sock.sendall(msg)

    def recvall(self, sock, n):
        # Helper: odbiera dokładnie n bajtów
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def recv_msg(self, sock):
        # Czyta 4 bajty nagłówka z długością paczki
        raw_msglen = self.recvall(sock, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Następnie czyta dokładnie tyle bajtów, ile zadeklarowano w nagłówku
        return self.recvall(sock, msglen)

    def connect(self):
        try:
            self.client.connect(self.addr)
            # Odbiera numer gracza po nowemu
            raw_data = self.recv_msg(self.client)
            return pickle.loads(raw_data)
        except socket.error as e:
            print("Błąd połączenia z serwerem:", e)

    def send(self, data):
        try:
            # Wysyła wciśnięte klawisze
            self.send_msg(self.client, pickle.dumps(data))
            # Czeka na cały kompletny stan gry
            raw_data = self.recv_msg(self.client)
            if raw_data:
                return pickle.loads(raw_data)
            return None
        except socket.error as e:
            print(e)
            return None
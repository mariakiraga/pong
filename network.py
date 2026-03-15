import socket
import pickle

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # UWAGA: Jeśli testujesz na jednym komputerze, zostaw "127.0.0.1"
        # Jeśli na dwóch różnych w WiFi, wpisz tu lokalne IP komputera, na którym działa serwer!
        self.server = "127.0.0.1"  
        self.port = 5555
        self.addr = (self.server, self.port)
        self.p = self.connect()

    def getP(self):
        return self.p

    def connect(self):
        try:
            self.client.connect(self.addr)
            # Odbiera od serwera numer gracza (0 lub 1)
            return pickle.loads(self.client.recv(2048))
        except socket.error as e:
            print("Błąd połączenia z serwerem:", e)

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            # Odbiera aktualny stan gry odesłany przez serwer
            return pickle.loads(self.client.recv(16384)) # Zwiększony bufor na stan gry
        except socket.error as e:
            print(e)
            return None
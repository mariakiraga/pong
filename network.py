# network.py
import socket
import pickle
import struct


def _send_msg(sock, msg):
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)


def _recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data


def _recv_msg(sock):
    raw_len = _recvall(sock, 4)
    if not raw_len:
        return None
    msglen = struct.unpack('>I', raw_len)[0]
    return _recvall(sock, msglen)


class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = "127.0.0.1" # change for your server's IPv4
        self.port = 5555
        self.player_id = None
        self._connect()

    def _connect(self):
        try:
            self.client.connect((self.server, self.port))
            # Step 1: receive player_id from server
            raw = _recv_msg(self.client)
            self.player_id = pickle.loads(raw)
        except Exception as e:
            print(f"Błąd połączenia: {e}")
            self.player_id = None

    def getP(self):
        return self.player_id

    def send_nick(self, nick: str):
        """
        Step 2 of handshake: send nickname, wait for "OK".
        The "OK" response is consumed here so it never leaks into the game loop.
        """
        try:
            _send_msg(self.client, pickle.dumps(f"NICK:{nick}"))
            raw = _recv_msg(self.client)
            ack = pickle.loads(raw) if raw else None
            if ack != "OK":
                print(f"Ostrzeżenie: nieoczekiwana odpowiedź serwera: {ack!r}")
        except Exception as e:
            print(f"Błąd wysyłania nicku: {e}")

    def send(self, data):
        """Send action string, receive game state dict."""
        try:
            _send_msg(self.client, pickle.dumps(data))
            raw = _recv_msg(self.client)
            if raw is None:
                return None
            result = pickle.loads(raw)
            # Safety net: if server accidentally sends a non-dict, discard it
            if not isinstance(result, dict):
                print(f"Nieoczekiwany typ odpowiedzi serwera: {type(result)} — pomijam")
                return None
            return result
        except Exception as e:
            print(f"Błąd send(): {e}")
            return None
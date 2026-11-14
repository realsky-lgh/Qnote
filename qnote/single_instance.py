"""
Single Instance IPC Mechanism for Qnote using QLocalServer & QLocalSocket
Ensures only one instance runs in background and handles 'qnote --toggle' calls.
"""
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

SOCKET_NAME = "qnote_single_instance_ipc_socket"

class SingleInstanceManager(QObject):
    message_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = None

    def try_connect_existing(self, message: str = "toggle") -> bool:
        """
        Attempts to connect to an existing running Qnote process.
        Returns True if an existing instance handled it.
        """
        socket = QLocalSocket()
        socket.connectToServer(SOCKET_NAME)
        if socket.waitForConnected(300):
            socket.write(message.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(300)
            # Give server a moment to read before terminating socket
            socket.waitForReadyRead(200)
            socket.disconnectFromServer()
            return True
        else:
            # Stale socket cleanup
            QLocalServer.removeServer(SOCKET_NAME)
            return False

    def start_listening(self) -> bool:
        """Starts the local server to receive IPC commands from other invocations."""
        # Clean up stale socket if crashed previously
        QLocalServer.removeServer(SOCKET_NAME)
        
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)
        return self.server.listen(SOCKET_NAME)

    def _on_new_connection(self):
        client_socket = self.server.nextPendingConnection()
        if client_socket:
            def handle_read():
                data = client_socket.readAll().data().decode("utf-8").strip()
                if data:
                    self.message_received.emit(data)
                # Reply ack
                client_socket.write(b"OK\n")
                client_socket.flush()
                client_socket.disconnectFromServer()

            if client_socket.bytesAvailable() > 0:
                handle_read()
            else:
                client_socket.readyRead.connect(handle_read)

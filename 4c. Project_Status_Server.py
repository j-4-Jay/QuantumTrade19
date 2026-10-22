"""QT19 Project Status quiet server. Serves Documentation/Project_Status on 127.0.0.1 and opens the page once."""
import functools, http.server, os, sys, threading, webbrowser

PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(HERE, "Documentation", "Project_Status")
URL = "http://127.0.0.1:%d/QT19_Project_Status.html" % PORT


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    handler = functools.partial(QuietHandler, directory=FOLDER)
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    except OSError:
        print("Project Status is already running. Opening the page.")
        webbrowser.open(URL)
        return
    print("Project Status is running at " + URL)
    print("Close this window to stop it.")
    threading.Timer(1.0, lambda: webbrowser.open(URL)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())

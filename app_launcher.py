"""Launch the local API and Streamlit dashboard from a Windows package."""

import logging
import os
from pathlib import Path
import socket
import sys
from threading import Thread
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

LOGGER = logging.getLogger("jade_launcher")


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _show_error(message: str) -> None:
    try:
        import tkinter
        from tkinter import messagebox
    except ImportError:
        print(message, file=sys.stderr)
        return

    try:
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Jade Dashboard", message, parent=root)
        root.destroy()
    except tkinter.TclError:
        print(message, file=sys.stderr)


def _prompt_serial_port() -> str | None:
    import tkinter
    from tkinter import simpledialog

    from serial.tools import list_ports

    available_ports = [port.device for port in list_ports.comports()]
    detected = ", ".join(available_ports) if available_ports else "nenhuma detectada"
    initial_value = available_ports[0] if len(available_ports) == 1 else ""
    root = tkinter.Tk()
    root.withdraw()
    try:
        value = simpledialog.askstring(
            "Jade Dashboard",
            f"Porta serial a observar ({detected}):\nExemplo: COM3",
            initialvalue=initial_value,
            parent=root,
        )
    finally:
        root.destroy()
    if value is None:
        return None
    port = value.strip()
    if not port:
        _show_error("Informe uma porta serial, como COM3, para iniciar o aplicativo.")
        return None
    return port


def _application_data_directory() -> Path:
    if sys.platform == "win32":
        base_directory = Path(
            os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    else:
        base_directory = Path(
            os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
    return base_directory / "JadeDashboard"


def _wait_for_url(url: str, service_thread: Thread, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not service_thread.is_alive():
            raise RuntimeError(f"O serviço local encerrou durante a inicialização: {url}.")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.2)
    raise RuntimeError(f"O serviço local não respondeu em {url}.")


def main() -> None:
    root = _resource_root()
    sys.path.insert(0, str(root))
    os.chdir(root)

    if not os.getenv("JADE_DATABASE_URL", "").strip():
        _show_error(
            "Configure JADE_DATABASE_URL com a conexão PostgreSQL do Supabase "
            "antes de abrir o Jade Dashboard. Consulte o README para obter os "
            "passos. Não compartilhe essa configuração: ela contém credenciais."
        )
        return

    log_directory = _application_data_directory()
    log_directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_directory / "jade.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_server = None
    api_thread = None
    try:
        serial_port = _prompt_serial_port()
        if serial_port is None:
            return
        os.environ["JADE_SERIAL_ENABLED"] = "true"
        os.environ["JADE_SERIAL_PORT"] = serial_port
        os.environ.setdefault("JADE_SERIAL_BAUDRATE", "115200")

        api_port = _available_port()
        dashboard_port = _available_port()
        api_url = f"http://127.0.0.1:{api_port}"
        os.environ["JADE_DATA_SOURCE"] = "api"
        os.environ["JADE_API_URL"] = api_url

        api_server = uvicorn.Server(
            uvicorn.Config(
                "backend.main:app",
                host="127.0.0.1",
                port=api_port,
                log_level="info",
                log_config=None,
            )
        )
        api_thread = Thread(target=api_server.run, name="jade-api", daemon=True)
        api_thread.start()

        _wait_for_url(f"{api_url}/health", api_thread)
        LOGGER.info("API local iniciada em %s", api_url)

        from streamlit.web import bootstrap

        dashboard_url = f"http://127.0.0.1:{dashboard_port}"
        streamlit_thread = Thread(
            target=bootstrap.run,
            args=(
                str(root / "frontend" / "app.py"),
                False,
                [],
                {
                    "server.address": "127.0.0.1",
                    "server.port": dashboard_port,
                    "server.headless": True,
                    "browser.gatherUsageStats": False,
                },
            ),
            name="jade-dashboard",
            daemon=True,
        )
        streamlit_thread.start()
        _wait_for_url(dashboard_url, streamlit_thread)
        webbrowser.open(dashboard_url)
        streamlit_thread.join()
    except KeyboardInterrupt:
        LOGGER.info("Aplicativo encerrado pelo usuário.")
    except Exception as exc:
        LOGGER.error("Falha ao iniciar o aplicativo (%s).", type(exc).__name__)
        _show_error(
            "Não foi possível iniciar o Jade Dashboard. Verifique a porta "
            "serial, a conectividade com o Supabase e as configurações. "
            "A categoria da falha foi registrada em log.\n\n"
            f"Consulte o log em {log_directory / 'jade.log'}."
        )
    finally:
        if api_server is not None:
            api_server.should_exit = True
        if api_thread is not None:
            api_thread.join(timeout=5)


if __name__ == "__main__":
    main()

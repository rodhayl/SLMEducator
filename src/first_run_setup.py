"""Local installation-owner setup. No HTTP route, token, or network listener."""

from __future__ import annotations

import getpass
import sys
import warnings
from scripts.seed_admin import create_first_admin, prepare_first_run

TEXT = {
    'es': {
        'title': 'Configurar el primer administrador',
        'intro': 'Esta instalación aún no tiene cuentas. Crea tu administrador antes de iniciar el servidor.',
        'username': 'Usuario (3–64 letras, números, punto, guion o guion bajo)',
        'password': 'Contraseña (mínimo 12 caracteres, mayúscula, minúscula, número y símbolo; máximo 72 bytes)',
        'repeat': 'Repite la contraseña', 'save': 'Crear administrador e iniciar', 'cancel': 'Cancelar',
        'invalid_username': 'Revisa el formato del usuario.',
        'invalid_password': 'La contraseña no cumple los requisitos indicados.',
        'invalid_repeat': 'Las contraseñas no coinciden.',
        'closed': 'La configuración inicial ya no está disponible. Cierra esta ventana e inicia de nuevo.',
        'recovery': ('Esta base ya existía y no admite crear otro administrador inicial. Utiliza la '
            'recuperación autorizada; no se cambiarán las cuentas existentes.'),
        'failed': 'No se pudo completar la configuración. No se iniciará el servidor.',
        'terminal': ('Abre el lanzador local para crear tu primer administrador. No se admite introducir '
            'contraseñas por una entrada redirigida.'),
    },
    'en': {
        'title': 'Set up the first administrator',
        'intro': 'This installation has no accounts yet. Create your administrator before starting the server.',
        'username': 'Username (3–64 letters, numbers, dot, hyphen or underscore)',
        'password': 'Password (at least 12 characters, uppercase, lowercase, number and symbol; at most 72 bytes)',
        'repeat': 'Repeat password', 'save': 'Create administrator and start', 'cancel': 'Cancel',
        'invalid_username': 'Check the username format.',
        'invalid_password': 'The password does not meet the requirements shown.',
        'invalid_repeat': 'The passwords do not match.',
        'closed': 'First-run setup is no longer available. Close this window and restart.',
        'recovery': ('This database already existed and is not eligible for initial setup. Use authorized '
            'recovery; existing accounts will not be changed.'),
        'failed': 'Setup could not be completed. The server will not start.',
        'terminal': 'Open the local launcher to create your first administrator. Redirected password input is not supported.',
    },
}


def _error_key(error: Exception) -> str:
    """Only known validation codes become UI text, never exception details."""
    code = str(error) if isinstance(error, ValueError) else ''
    return 'invalid_' + code if code in {'username', 'password', 'repeat'} else 'closed' if code == 'closed' else 'failed'


def _console_setup(strings: dict[str, str]) -> bool:
    """Read passwords only from the user's interactive terminal, never echo them."""
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print(strings['terminal'])
        return False
    print(strings['intro'])
    try:
        username = input(strings['username'] + ': ').strip()
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            password = getpass.getpass(strings['password'] + ': ')
            repeat = getpass.getpass(strings['repeat'] + ': ')
        create_first_admin(username, password, repeat)
        return True
    except (KeyboardInterrupt, EOFError):
        return False
    except Exception as error:
        print(strings[_error_key(error)])
        return False


def _native_setup(strings: dict[str, str], state: str) -> bool:
    """Use a local masked native dialog before any server process exists."""
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title(strings['title'])
    completed = False
    if state != 'needed':
        root.withdraw()
        messagebox.showerror(strings['title'], strings['recovery'], parent=root)
        root.destroy()
        return False
    root.columnconfigure(0, weight=1)
    frame = ttk.Frame(root, padding=24)
    frame.grid(sticky='nsew')
    frame.columnconfigure(0, weight=1)
    ttk.Label(frame, text=strings['intro'], wraplength=540).grid(row=0, column=0, sticky='w', pady=(0, 16))
    fields = {}
    for index, key in enumerate(('username', 'password', 'repeat')):
        ttk.Label(frame, text=strings[key], wraplength=540).grid(row=index * 2 + 1, column=0, sticky='w')
        entry = ttk.Entry(frame, show='' if key == 'username' else '•', width=48)
        entry.grid(row=index * 2 + 2, column=0, sticky='ew', pady=(4, 12))
        fields[key] = entry
    status = ttk.Label(frame, text='', wraplength=540)
    status.grid(row=7, column=0, sticky='w')

    def submit() -> None:
        nonlocal completed
        try:
            create_first_admin(fields['username'].get().strip(), fields['password'].get(), fields['repeat'].get())
        except Exception as error:
            key = _error_key(error)
            status.configure(text=strings[key])
            if key.startswith('invalid_'):
                fields[key.removeprefix('invalid_')].focus_set()
            return
        completed = True
        root.destroy()

    ttk.Button(frame, text=strings['save'], command=submit).grid(row=8, column=0, sticky='ew', pady=(12, 4))
    ttk.Button(frame, text=strings['cancel'], command=root.destroy).grid(row=9, column=0, sticky='ew')
    root.bind('<Return>', lambda event: submit())
    root.bind('<Escape>', lambda event: root.destroy())
    fields['username'].focus_set()
    root.mainloop()
    return completed


def ensure_initial_admin(*, gui: bool = True, language: str = 'es') -> bool:
    """Finish local setup or stop safely; established installations are untouched."""
    strings = TEXT.get(language, TEXT['es'])
    try:
        state = prepare_first_run()
    except Exception:
        print(strings['failed'])
        return False
    if state == 'configured':
        return True
    if gui:
        try:
            return _native_setup(strings, state)
        except ImportError:
            pass
        except Exception:
            # A headless machine can use its local terminal, never a web claim.
            pass
    if state != 'needed':
        print(strings['recovery'])
        return False
    return _console_setup(strings)

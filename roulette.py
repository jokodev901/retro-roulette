import json
import pathlib
import random
import subprocess
import sys
import time
import configparser

from pynput import keyboard


class RetroRoulette:
    def __init__(self, base_path: pathlib.Path = None):
        self.listener = None
        self.active = True
        self.base_path = base_path
        self.retroarch_exe = self._get_executable_path()
        self.playlist_path = self._get_playlist_path()
        self.current_proc: subprocess.Popen | None = None
        self.roms: list[dict[str, str]] = self._load_playlists()

    def _quit(self):
        self._kill_proc()
        self.active = False

    def _get_executable_path(self) -> pathlib.Path | str:
        """
        Determines the correct RetroArch executable path based on the host OS.
        Returns a pathlib.Path object for local executables, or a string for
        system PATH commands.
        """
        # Windows
        if sys.platform == "win32":
            if not self.base_path:
                self.base_path = pathlib.Path(r'C:\Retroarch')

            return self.base_path.joinpath('retroarch.exe')

        # MacOS
        elif sys.platform == "darwin":
            if not self.base_path:
                self.base_path = pathlib.Path(r'Applications/')
            return self.base_path.joinpath('RetroArch.app/Contents/MacOS/RetroArch')

        # Linux
        else:
            local_bin = self.base_path.joinpath('retroarch')
            # If a local binary exists in the base_path, use it.
            # Otherwise, return the string 'retroarch' to rely on the system PATH.
            if local_bin.exists():
                return local_bin
            return 'retroarch'

    def _get_playlist_path(self) -> pathlib.Path:
        """
        Check retroarch.cfg to get playlist directory path
        """
        # Windows
        if sys.platform == "win32":
            if not self.base_path:
                self.base_path = pathlib.Path(r'C:\Retroarch')

            file = self.base_path.joinpath('retroarch.cfg')

            try:
                with (file.open('r', encoding='utf-8') as f):
                    for line in f:
                        var = line.split(' = ')

                        if var[0] == 'playlist_directory':
                            pl_val = var[1].strip()

                            if pl_val.startswith('":'):
                                pl_val = pl_val \
                                    .replace(':', '') \
                                    .replace('"', '') \
                                    .replace('\\', '')
                                return self.base_path.joinpath(pl_val)

                            return pathlib.Path(var[1].replace('"', ''))

            except FileNotFoundError:
                print('Could not find retroarch.cfg in the provided directory.')
                sys.exit(1)

        # MacOS
        # Linux

        return pathlib.Path('')

    def _load_playlists(self) -> list[dict[str, str]]:
        roms = []
        playlists_dir = self.playlist_path

        for file in playlists_dir.glob('*.lpl'):
            with file.open('r', encoding='utf-8') as f:
                playlist = json.load(f)
                default_core = playlist.get('default_core_path', 'DETECT')

                for item in playlist.get('items', []):
                    core = item.get('core_path')
                    label = item.get('label')
                    if core == 'DETECT':
                        core = default_core

                    roms.append({
                        'label': label,
                        'core': core,
                        'path': item.get('path')
                    })

        if not roms:
            print("No valid playlists or ROMs found in the specified directory, exiting")
            sys.exit(1)

        return roms

    def _kill_proc(self) -> None:
        if self.current_proc is not None:
            if self.current_proc.poll() is None:
                self.current_proc.kill()
                self.current_proc.wait()
            self.current_proc = None

    def launch_random(self) -> None:
        self._kill_proc()

        # Reload roms if list has been exhausted
        if not self.roms:
            print("No remaining ROMs available in the playlists, reloading all playlists")
            self.roms = self._load_playlists()

        rand_index = random.randrange(len(self.roms))
        rom_data = self.roms.pop(rand_index)

        print(f"Now playing: {rom_data['label']}")

        cmd = [
            str(self.retroarch_exe),
            "-L", rom_data['core'],
            rom_data['path']
        ]

        self.current_proc = subprocess.Popen(cmd)

    def run(self) -> None:
        print("Retro Roulette is now running, you may minimize this window")
        print("Press ctrl+alt+r to roll a random game, or ctrl+alt+q to quit")

        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+r': self.launch_random,
            '<ctrl>+<alt>+q': self._quit,
        })
        self.listener.start()

        try:
            while self.active:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nProgram terminated")
        finally:
            self.listener.stop()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    path = pathlib.Path(config['Retroarch']['path'])
    app = RetroRoulette(path)
    app.run()

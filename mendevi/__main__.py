#!/usr/bin/env python

"""Command line interface entry point."""

import importlib

import click


class LazyGroup(click.Group):
    """Overwite clik.Group to lasy import."""

    def __init__(self, *args: tuple, **kwargs: dict) -> None:
        """Group initialisation."""
        self._lazy_commands = {}
        super().__init__(*args, **kwargs)

    def add_lazy_command(self, import_path: str, name: str) -> None:
        """Register a command without importing it immediately."""
        self._lazy_commands[name] = import_path

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command:
        """Import the function of the module."""
        if cmd_name in self._lazy_commands:
            module_path, func_name = self._lazy_commands[cmd_name].rsplit(".", 1)
            mod = importlib.import_module(module_path)
            return getattr(mod, func_name)
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List all available command names (including lazy ones)."""
        cmds = set(super().list_commands(ctx))
        cmds.update(self._lazy_commands.keys())
        return sorted(cmds)


@click.group(cls=LazyGroup)
def main() -> None:
    """Perform video transcoding measurements."""


# same as main.add_command but with lazy import
main.add_lazy_command("mendevi.cli.decode.main", "decode")
main.add_lazy_command("mendevi.cli.doc.main", "doc")
main.add_lazy_command("mendevi.cli.download.main", "download")
main.add_lazy_command("mendevi.cli.encode.main", "encode")
main.add_lazy_command("mendevi.cli.g5k.main", "g5k")
main.add_lazy_command("mendevi.cli.json.main", "json")
main.add_lazy_command("mendevi.cli.merge.main", "merge")
main.add_lazy_command("mendevi.cli.plot.main", "plot")
main.add_lazy_command("mendevi.cli.prepare.main", "prepare")
main.add_lazy_command("mendevi.cli.probe.main", "probe")
main.add_lazy_command("mendevi.cli.test.main", "test")
main.add_lazy_command("mendevi.cli.version.main", "version")


if __name__ == "__main__":
    main()

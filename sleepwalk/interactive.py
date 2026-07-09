from __future__ import annotations

import sys
from dataclasses import dataclass

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.containers import Window

from .config import Config, save_config, with_sessions
from .detector import detect, format_duration
from .tmux import capture_pane, list_sessions


@dataclass
class Row:
    target: str
    selected: bool
    state: str = "unknown"
    reset: str = "-"


@dataclass
class PickerState:
    rows: list[Row]
    cursor: int = 0
    confirming: bool = False


def run_wizard(config: Config) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("sleepwalk interactive picker needs a TTY", file=sys.stderr)
        return 2

    rows = build_rows(config)
    if not rows:
        print("No tmux sessions found.")
        return 0

    state = PickerState(rows)
    bindings = KeyBindings()

    def selected_targets() -> list[str]:
        return [row.target for row in state.rows if row.selected]

    def finish(result: list[str] | None = None) -> None:
        app.exit(result=result)

    @bindings.add(Keys.Escape, eager=True)
    @bindings.add(Keys.ControlC, eager=True)
    @bindings.add(Keys.ControlQ, eager=True)
    def _cancel(event) -> None:
        finish(None)

    @bindings.add(Keys.Up, eager=True)
    @bindings.add("k", eager=True)
    def _up(event) -> None:
        if state.confirming:
            state.confirming = False
            return
        state.cursor = max(0, state.cursor - 1)

    @bindings.add(Keys.Down, eager=True)
    @bindings.add("j", eager=True)
    def _down(event) -> None:
        if state.confirming:
            state.confirming = False
            return
        state.cursor = min(len(state.rows) - 1, state.cursor + 1)

    @bindings.add(" ", eager=True)
    def _toggle(event) -> None:
        if state.confirming:
            state.confirming = False
            return
        state.rows[state.cursor].selected = not state.rows[state.cursor].selected

    @bindings.add(Keys.Enter, eager=True)
    def _enter(event) -> None:
        if state.confirming:
            finish(selected_targets())
        else:
            state.confirming = True

    @bindings.add("y", eager=True)
    @bindings.add("Y", eager=True)
    def _yes(event) -> None:
        if state.confirming:
            finish(selected_targets())

    @bindings.add("n", eager=True)
    @bindings.add("N", eager=True)
    def _no(event) -> None:
        if state.confirming:
            state.confirming = False

    control = FormattedTextControl(lambda: render(state), focusable=True)
    height = min(len(rows) + 5, 18)
    app = Application(
        layout=Layout(Window(control, height=Dimension.exact(height), always_hide_cursor=True)),
        key_bindings=bindings,
        full_screen=False,
        mouse_support=False,
    )

    selected = app.run()
    if selected is None:
        print("cancelled")
        return 130

    save_config(with_sessions(config, selected))
    print(f"saved {len(selected)} session(s)")
    return 0


def build_rows(config: Config) -> list[Row]:
    selected = {session.target for session in config.sessions if session.enabled}
    rows = [Row(target=name, selected=name in selected) for name in list_sessions(config.tmux_socket)]
    for row in rows:
        try:
            detection = detect(capture_pane(row.target, config.tmux_socket))
            row.state = "limited" if detection.state == "limited" else "ok"
            row.reset = format_duration(detection.reset_in)
        except Exception as exc:
            row.state = "error"
            row.reset = "-"
    return rows


def render(state: PickerState) -> FormattedText:
    lines: list[tuple[str, str]] = []
    lines.append(("class:title", "sleepwalk  "))
    lines.append(("", "Space: select  Enter: confirm  Esc: cancel\n\n"))
    lines.append(("class:muted", f"{'':2} {'':3} {'session':24} {'state':10} {'reset':10}\n"))

    visible_rows = visible_slice(state.rows, state.cursor)
    for index, row in visible_rows:
        style = "class:selected" if index == state.cursor and not state.confirming else ""
        pointer = ">" if index == state.cursor and not state.confirming else " "
        marker = "[x]" if row.selected else "[ ]"
        lines.append((style, f"{pointer} {marker} {row.target:24.24} {row.state:10.10} {row.reset:10.10}\n"))

    if state.confirming:
        count = len([row for row in state.rows if row.selected])
        lines.append(("", "\n"))
        lines.append(("class:confirm", f"Save {count} selected session(s)?  Enter/y: yes  n: back  Esc: cancel"))

    return FormattedText(lines)


def visible_slice(rows: list[Row], cursor: int) -> list[tuple[int, Row]]:
    max_rows = 12
    start = min(max(0, cursor - max_rows + 1), max(0, len(rows) - max_rows))
    return list(enumerate(rows[start : start + max_rows], start=start))

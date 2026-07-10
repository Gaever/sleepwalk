# sleepwalk

Консольная утилита для VPS, где ИИ-агенты работают в отдельных `tmux`-сессиях и
останавливаются из-за лимитов.

`sleepwalk` следит за выбранными сессиями. Когда лимит сброшен, он отправляет
агенту:

```text
продолжай
```

## Установка агентом

Скопируйте этот промпт агенту на VPS:

```text
Установи sleepwalk:
1. Клонируй git@github.com:Gaever/sleepwalk.git в ~/sleepwalk.
2. Создай виртуальное окружение: python3 -m venv ~/sleepwalk/.venv.
3. Установи проект: ~/sleepwalk/.venv/bin/pip install -e ~/sleepwalk.
4. Создай ссылку: ln -sf ~/sleepwalk/.venv/bin/sleepwalk ~/.local/bin/sleepwalk.
5. Проверь, что команда sleepwalk доступна из любого каталога.
6. Запусти sleepwalk, дай мне выбрать tmux-сессии.
7. После выбора выполни sleepwalk install-systemd.
8. Проверь systemctl --user status sleepwalk.timer.
```

## Установка вручную

```bash
git clone git@github.com:Gaever/sleepwalk.git ~/sleepwalk
python3 -m venv ~/sleepwalk/.venv
~/sleepwalk/.venv/bin/pip install -e ~/sleepwalk
mkdir -p ~/.local/bin
ln -sf ~/sleepwalk/.venv/bin/sleepwalk ~/.local/bin/sleepwalk
sleepwalk
sleepwalk install-systemd
systemctl --user status sleepwalk.timer
```

Если `~/.local/bin` не в `PATH`, добавьте его в настройки командной оболочки.

## Выбор сессий

```bash
sleepwalk
```

Управление:

- `↑`/`↓` или `j`/`k` — перемещение.
- `Space` — выбрать или снять выбор.
- `Enter` — подтвердить.
- `Esc` — выйти без сохранения.

Пример:

```text
sleepwalk  Space: select  Enter: confirm  Esc: cancel

       session                  state      reset
> [ ] agy                      limited    2h47m
  [ ] claude                   ok         -
  [x] reelser                  limited    2h06m
```

`state`:

- `ok` — агент не стоит на лимите.
- `limited` — агент стоит на лимите.

`reset` — сколько осталось до сброса лимита, если время удалось прочитать.

## Команды

```bash
sleepwalk status
```

Показать состояние выбранных сессий.

```bash
sleepwalk tick
```

Проверить выбранные сессии один раз и отправить `продолжай`, если время сброса
известно и уже подошло.

```bash
sleepwalk add <session> [session...]
```

Добавить сессии вручную.

```bash
sleepwalk remove <session> [session...]
```

Убрать сессии.

```bash
sleepwalk list
```

Показать выбранные сессии.

```bash
sleepwalk paths
```

Показать пути к конфигу и логу.

```bash
sleepwalk install-systemd
```

Включить проверку по расписанию.

```bash
sleepwalk uninstall-systemd
```

Отключить проверку по расписанию.

## Расписание

`sleepwalk install-systemd` создаёт:

```text
~/.config/systemd/user/sleepwalk.service
~/.config/systemd/user/sleepwalk.timer
```

Таймер запускает:

```bash
sleepwalk tick
```

раз в 30 минут.

Проверить:

```bash
systemctl --user status sleepwalk.timer
journalctl --user -u sleepwalk.service
```

## Файлы

```text
~/.config/sleepwalk/config.toml
~/.local/state/sleepwalk/state.json
~/.local/state/sleepwalk/sleepwalk.log
```

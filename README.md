# sleepwalk

`sleepwalk` — небольшая CLI-утилита для VPS, где AI-агенты живут в отдельных
`tmux`-сессиях и иногда останавливаются из-за usage/rate limits.

Идея простая: вы один раз выбираете tmux-сессии, за которыми нужно следить, а
`sleepwalk` периодически смотрит на экран каждой сессии. Если агент стоит на
экране лимита и время сброса уже подошло, утилита отправляет в эту сессию:

```text
продолжай
```

Это не менеджер агентов и не замена Codex/Claude/других CLI. Это маленький
watchdog для development sandbox, где хочется оставить несколько агентов
работать, не возвращаясь вручную к каждому после сброса лимитов.

## Зачем это нужно

На dev VPS часто удобно держать несколько агентов параллельно:

- один чинит backend;
- другой гоняет frontend-тесты;
- третий разбирает issue;
- четвёртый ждёт долгую сборку или лимит провайдера.

Когда CLI-агент упирается в лимит, он обычно остаётся открытым в tmux и пишет
что-то вроде:

```text
Usage limit reached
You've hit your session limit · resets 10:40pm (Asia/Jakarta)
Individual quota reached. Resets in 2h47m19s.
```

`sleepwalk` автоматизирует скучную часть: дождаться reset window и в нужный
момент отправить короткое продолжение.

## Возможности

- Интерактивный выбор tmux-сессий через удобное inline-меню.
- Бинарный статус сессии: `limited` или `ok`.
- Показ оставшегося времени до reset, если его удалось распарсить.
- Поддержка относительного времени: `Resets in 2h47m19s`.
- Поддержка абсолютного времени: `resets 10:40pm (Asia/Jakarta)`.
- Запуск по расписанию через `systemd --user`.
- Без фонового демона: systemd timer раз в 30 минут запускает один короткий
  `sleepwalk tick`.

## Требования

- Linux с `tmux`.
- Python 3.11+.
- `prompt_toolkit`.
- `systemd --user`, если нужен автоматический запуск по расписанию.

## Установка

Сейчас проект рассчитан на запуск из checkout-а. Клонируйте репозиторий и
добавьте launcher в `PATH`:

```bash
git clone git@github.com:Gaever/sleepwalk.git
cd sleepwalk
ln -sf "$PWD/bin/sleepwalk" ~/.local/bin/sleepwalk
```

После этого команда доступна из любого каталога:

```bash
sleepwalk status
```

## Быстрый старт

Откройте интерактивный выбор сессий:

```bash
sleepwalk
```

Управление:

- `↑`/`↓` или `j`/`k` — перемещение.
- `Space` — выбрать или снять выбор с tmux-сессии.
- `Enter` — перейти к подтверждению.
- `Enter`/`y` — сохранить выбор.
- `n` — вернуться из подтверждения.
- `Esc` или `Ctrl-C`/`Ctrl-Q` — выйти без сохранения.

Пример экрана:

```text
sleepwalk  Space: select  Enter: confirm  Esc: cancel

       session                  state      reset
> [ ] agy                      limited    2h47m
  [ ] claude                   ok         -
  [x] reelser                  limited    2h06m
```

После выбора можно проверить состояние:

```bash
sleepwalk status
```

Пример:

```text
reelser: limited reset=2h06m
```

## Команды

```bash
sleepwalk
```

Открыть интерактивный выбор tmux-сессий.

```bash
sleepwalk status
```

Показать состояние отслеживаемых сессий.

```bash
sleepwalk tick
```

Сделать один проход по отслеживаемым сессиям. Если агент стоит на лимите и
reset уже близко или не указан явно, `sleepwalk` отправит `продолжай`.

```bash
sleepwalk add <session> [session...]
```

Добавить tmux-сессии вручную.

```bash
sleepwalk remove <session> [session...]
```

Убрать tmux-сессии из отслеживания.

```bash
sleepwalk list
```

Показать список отслеживаемых сессий.

```bash
sleepwalk paths
```

Показать пути к конфигу и логу.

```bash
sleepwalk install-systemd
```

Установить и включить user-level systemd timer.

```bash
sleepwalk uninstall-systemd
```

Отключить и удалить user-level systemd timer/service.

## Как работает systemd-интеграция

Команда:

```bash
sleepwalk install-systemd
```

создаёт два файла в:

```text
~/.config/systemd/user/
```

Файлы:

```text
sleepwalk.service
sleepwalk.timer
```

`sleepwalk.service` — это `oneshot`-service. Он не висит постоянно в фоне, а
просто запускает один проход:

```bash
python3 -m sleepwalk tick
```

`sleepwalk.timer` запускает этот service:

- через 2 минуты после старта user systemd;
- затем раз в 30 минут;
- с `Persistent=true`, чтобы systemd мог догнать пропущенный запуск после
  простоя пользователя/машины.

После записи unit-файлов `sleepwalk` выполняет:

```bash
systemctl --user daemon-reload
systemctl --user enable --now sleepwalk.timer
```

Проверить timer:

```bash
systemctl --user status sleepwalk.timer
systemctl --user list-timers sleepwalk.timer
```

Посмотреть логи запусков:

```bash
journalctl --user -u sleepwalk.service
```

Отключить интеграцию:

```bash
sleepwalk uninstall-systemd
```

Эта команда делает `disable --now` для timer, удаляет unit-файлы и запускает
`systemctl --user daemon-reload`.

## Конфиг и состояние

Конфиг:

```text
~/.config/sleepwalk/config.toml
```

Пример:

```toml
interval_seconds = 1800
resume_text = "продолжай"

[[sessions]]
target = "reelser"
enabled = true
cooldown_seconds = 1800
```

State и лог:

```text
~/.local/state/sleepwalk/state.json
~/.local/state/sleepwalk/sleepwalk.log
```

`cooldown_seconds` защищает от повторной отправки `продолжай` в одну и ту же
сессию слишком часто.

## Как определяется лимит

`sleepwalk` читает последние строки tmux-pane через `tmux capture-pane` и ищет
типичные сообщения лимитов:

- `usage limit`
- `Usage limit reached`
- `You've reached your usage limit. Try again after your limit resets.`
- `rate limit`
- `limit reached`
- `resets in ...`
- `resets 10:40pm (Asia/Jakarta)`
- `Individual quota reached`

Если лимит найден, состояние становится `limited`. Всё остальное в публичном
выводе считается `ok`.

## Безопасность поведения

`sleepwalk` не перезапускает процессы, не закрывает tmux-сессии и не выполняет
команды внутри shell. Он только отправляет текст `продолжай` в выбранную
tmux-сессию, когда считает, что агент стоит на лимите.

Перед включением systemd timer удобно вручную проверить:

```bash
sleepwalk status
sleepwalk tick
```

## Статус проекта

Проект родился как личная утилита для VPS-песочницы с несколькими AI-агентами.
API и формат конфига пока могут меняться.

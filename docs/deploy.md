# Развёртывание на сервере (Ubuntu, Docker Compose)

Образ собирается на сервере из репозитория: фронт (`web/`) и сервис (`app/`, `recsys/`).
Данные в образ и в git не входят — три файла кладутся в `data/` рядом с `docker-compose.yml`
и монтируются только на чтение. Обогащение и сборка индексов на сервере не запускаются.

## Первый запуск

На сервере (Docker с плагином compose):

    git clone https://github.com/zhurich/rlt-hack.git && cd rlt-hack
    mkdir -p data

С рабочей машины — данные (~685 МБ), из корня проекта:

    scp data/index.pkl data/pool.pkl data/rlt.duckdb user@server:~/rlt-hack/data/

Рядом с `rlt.duckdb` не должно быть файла `rlt.duckdb.wal`: копировать базу, когда `enrich.*`
и `scripts/load.py` не работают.

На сервере:

    docker compose up -d --build
    docker compose logs -f app        # ждать «Application startup complete», ~10–20 с

Страница — `http://<сервер>:8010/`. Другой порт: `PORT=80 docker compose up -d`.
Памяти нужно около 2 ГБ.

## Обновление

Репозиторий приватный, доступа к GitHub у сервера нет, поэтому `git pull` там не работает.
Код отправляется с рабочей машины прямо в репозиторий на сервере, в ветку `deploy`:

    git push ssh://user@server/root/rlt-hack main:deploy

На сервере:

    git merge --ff-only deploy && docker compose up -d --build --force-recreate

После пересборки индексов или обогащения — скопировать изменившиеся файлы в `data.new/`,
на сервере переложить их в `data/` (прежние — в `data.old/` на случай отката) и пересоздать
контейнер той же командой: сервис читает данные один раз при старте. Данные и код обновлять
вместе — со старым индексом новые лоты отдают ошибку 500.

## Если не стартует

- `ModuleNotFoundError`, ошибки `pickle` или предупреждения о версии scikit-learn — индексы
  собраны другими версиями библиотек, чем в `requirements.txt`. Версии там закреплены по
  окружению, в котором индексы собирались; после обновления библиотек локально — обновить и файл.
- `IO Error` от DuckDB — база записана другой версией DuckDB либо рядом лежит `.wal`.
- Страница отдаёт 503 — фронт не собрался, смотреть вывод `docker compose build`.

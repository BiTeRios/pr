# Лабораторная работа №6

## Тема
Настройка CI/CD с помощью GitHub Actions: сборка Docker-контейнеров, тестирование и публикация образов на Docker Hub.

## Что добавлено

В проект добавлен workflow:

```text
.github/workflows/ci-cd.yml
```

Он автоматически запускается при `push` или `pull_request` в ветки `main` и `master`.

## Что делает workflow

1. Скачивает код репозитория.
2. Собирает Docker-образ backend.
3. Собирает Docker-образ frontend.
4. Создаёт Docker Network `todo_net`.
5. Запускает контейнеры:
   - `todo_db` — PostgreSQL;
   - `todo_mail` — GreenMail SMTP/IMAP/POP3;
   - `todo_backend` — FastAPI backend;
   - `todo_frontend` — React frontend.
6. Проверяет backend и frontend через `curl`.
7. Проверяет REST API:
   - `GET /health`;
   - `GET /tasks`;
   - `POST /tasks`;
   - `GET /tasks/{id}`;
   - `PUT /tasks/{id}`.
8. Проверяет почтовую часть:
   - отправку письма через SMTP;
   - проверку IMAP;
   - проверку POP3.
9. Останавливает контейнеры и удаляет тестовые образы.
10. При `push` публикует образы на Docker Hub:
    - `todo-backend`;
    - `todo-frontend`.

## Какие GitHub Secrets нужны

В репозитории нужно добавить два секрета:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Пример:

```text
DOCKERHUB_USERNAME = vederminov
DOCKERHUB_TOKEN = токен доступа Docker Hub
```

## Как добавить secrets в GitHub

1. Открыть репозиторий на GitHub.
2. Перейти в `Settings`.
3. Открыть `Secrets and variables`.
4. Выбрать `Actions`.
5. Нажать `New repository secret`.
6. Добавить `DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN`.

## Что показать преподавателю

1. Файл `.github/workflows/ci-cd.yml`.
2. Вкладку `Actions` в GitHub.
3. Успешный запуск workflow.
4. Шаги сборки образов backend и frontend.
5. Шаги запуска контейнеров.
6. Проверки через `curl`.
7. Очистку контейнеров.
8. Образы, загруженные на Docker Hub.

## Краткое объяснение для защиты

В лабораторной работе №6 я настроил CI/CD через GitHub Actions. После загрузки кода в репозиторий workflow автоматически собирает Docker-образы frontend и backend, запускает все контейнеры приложения, проверяет работоспособность backend, frontend, REST API и почтовых endpoints через `curl`, затем очищает контейнеры и тестовые образы. После успешной проверки workflow публикует собранные Docker-образы на Docker Hub.

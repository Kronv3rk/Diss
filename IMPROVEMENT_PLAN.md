# ach-experiment - аудит качества и план улучшений

Аудит проведён на реальных инструментах (ruff, mypy, pytest-coverage, radon) и анализе всех веток.
Дата: 2026-06-08. Кодовая база: ~3 200 строк Python, 57 тестов.

---

## TL;DR - 5 вещей, которые дают наибольший прирост качества

1. **🔴 Научная корректность под угрозой.** Фикс «BoundedLoads v_min parity» **не влит в `main`**. На `main`
   базлайн Bounded-Loads сравнивается нечестно (может опустошать узлы до 1 токена, тогда как ACH держит ≥3).
   После фикса в серии C3: **1568 нарушений инвариантов → 0**, а преимущество ACH над Bounded-Loads
   падает с **−23.5% до −3.5%** (p: 6e-6 → 8e-5). **Цифры в дипломе, взятые из `main`, нужно пересчитать.**
2. **🔴 Покрытие 19%.** Ядро не тестируется: `experiment.py` - 0%, `metrics.py` (метрика D, на которой держатся все выводы) - 0%, генератор нагрузки и шум - 0%. Хорошо покрыт только ACH (90%) и кольцо.
3. **🟠 Нет статистической поправки на множественные сравнения** (Bonferroni/Holm/BH). Десятки Wilcoxon-тестов с «сырыми» p-value завышают риск ложных открытий.
4. **🟠 Нет инфраструктуры качества на `main`:** ни `pyproject.toml`, ни CI (GitHub Actions есть только в неслитой ветке), `README.md` = 6 байт, нет `LICENSE`.
5. **🟡 Воспроизводимость не зафиксирована:** зависимости с `>=` (не пины), в результатах не сохраняется git-SHA/хэш конфига/сиды.

---

## 1. Ветки: что несмёржено и что с этим делать

| Ветка | Δ к `origin/main` | Содержимое | Рекомендация |
|---|---|---|---|
| `main` | - | Источник истины, но **без** фикса BoundedLoads | Влить P0-фикс, пересчитать результаты |
| `claude/ach-ring-experiment-1llkY` | +1 / −6 | 1 несмёрженный коммит `d445a34`: фикс v_min у Bounded-Loads (`bounded_loads.py`, `experiment.py`, пересчёт `all_results.json`) | **Смёржить / cherry-pick в `main` (P0)** |
| `codex-c-dzz-run` | +4 / −0 | Серия **C-DZZ** (`series_c-dzz.yaml`, склад тайлов ДЗЗ, Zipf=0.8), **CI-workflow** `.github/workflows/c-dzz.yml`, правка `build_all_results.py` | Обобщить workflow в полноценный CI; серию - оценить и при необходимости влить |

Важные нюансы по `codex-c-dzz-run`:
- Workflow запускается только на `push` в саму ветку и вручную (`workflow_dispatch`); это не общий CI на тесты для `main`.
- Конфиг C-DZZ полагается на `extends: base` (поддерживается). Но ключи `node_classes` и `domain` **движок симуляции не читает** - это документация. Фактически C-DZZ ≈ «C1 + Zipf 0.8» (постоянная нагрузка, без оттока узлов). Не вводит новой механики.
- Ветка **не содержит** фикса BoundedLoads → если результаты C-DZZ уже считались, они тоже на «нечестном» базлайне.

**Действие:** свести три ветки в одну линию. Порядок: (1) влить фикс BoundedLoads в `main`; (2) поверх - обобщённый CI; (3) решить судьбу серии C-DZZ. После слияния удалить отработавшие ветки.

---

## 2. P0 - научная корректность (делать в первую очередь)

### 2.1 Влить фикс BoundedLoads и пересчитать ВСЕ результаты
Цена бездействия: ключевая таблица результатов в дипломе завышает преимущество ACH. После слияния нужно:
- пересобрать `results/all_results.json` (`run_all.py` → `build_all_results.py`),
- заново сгенерировать таблицы (`analyze.py`) и графики (`plot_traces.py`),
- обновить все числа и выводы в тексте диссертации (особенно по C3 и любым агрегатам «ACH vs Bounded-Loads»).

### 2.2 Покрыть тестами то, на чём держатся выводы
Сейчас `metrics.py` (метрика **D**) и `experiment.run_experiment` - **0%**. Любая ошибка здесь
тихо искажает все результаты (как и случилось с базлайном). Минимум:
- `test_metrics.py`: `compute_D` на известных входах (идеально равная нагрузка → D=0; заданный перекос → известное D).
- `test_experiment_smoke.py`: короткий прогон (`T=20`, 1 сид) - проверка формы выхода, отсутствия NaN, срабатывания инвариантов = 0.
- `test_baselines.py`: для каждого из 4 базлайнов - соблюдение `v_min`, отсутствие нарушений (этот тест поймал бы баг BoundedLoads).
- `test_determinism.py`: один и тот же сид → побитово одинаковые D (golden-value).

### 2.3 Поправка на множественные сравнения
В `analyze.py` / `build_all_results.py` p-value Wilcoxon идут без коррекции. Добавить Holm или Benjamini-Hochberg:

```python
from scipy.stats import false_discovery_control  # SciPy ≥1.11
# собрать все p в список p_raw в фиксированном порядке, затем:
p_adj = false_discovery_control(p_raw, method="bh")   # или Holm через statsmodels.multipletests
```
Хранить в JSON и `p_raw`, и `p_adj`; в тексте опираться на скорректированные.

---

## 3. P1 - тесты, упаковка, CI, воспроизводимость

### 3.1 Поднять покрытие (цель ≥70%)
Текущая картина (`coverage`): `experiment.py` 0%, `cluster.py` 0%, `metrics.py` 0%, `load_generator.py` 0%,
`noise_model.py` 0%, все `scripts/` 0%; базлайны `dynamic_r` 9%, `bounded_loads` 17%, `static_weighted` 18%.
Добавить тесты на генератор нагрузки (распределение Zipf), модель шума (sigma/lag/p_miss), кластер, и smoke-тесты на скрипты.

### 3.2 Сделать проект устанавливаемым пакетом (убрать `sys.path.insert`)
Сейчас каждый скрипт делает `sys.path.insert(0, "..")`. Заменить на нормальную упаковку:

```toml
# ach-experiment/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "ach-experiment"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["numpy>=1.24,<3", "scipy>=1.10", "matplotlib>=3.7", "pandas>=2.0", "pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=7.4", "pytest-cov", "ruff", "mypy"]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.ruff]
line-length = 100
[tool.pytest.ini_options]
testpaths = ["tests"]
```
Тогда `pip install -e .` и `from src...` работают без хаков. Плюс `conftest.py` (на время переходного периода):

```python
# ach-experiment/conftest.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
```

### 3.3 CI на `main` (GitHub Actions)
Обобщить неслитый workflow в нормальный CI на каждый push/PR:

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: ach-experiment } }
    strategy: { matrix: { python-version: ["3.10", "3.11", "3.12"] } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}", cache: pip }
      - run: pip install -r requirements.txt ruff mypy pytest-cov
      - run: ruff check .
      - run: mypy src --ignore-missing-imports
      - run: pytest -q --cov=src --cov-report=term-missing --cov-fail-under=70
```

### 3.4 Воспроизводимость
- **Запинить зависимости** для прогонов, дающих числа диплома: добавить `requirements.lock` (точные версии, `pip freeze`).
- **Провенанс в результатах**: в каждый `run_*.json` и в `all_results.json` писать git-SHA, SHA256 конфига, версии numpy/scipy, базовый сид. Тогда любую таблицу можно проследить до кода.
- `Dockerfile` или `environment.yml` для точного окружения (на случай защиты/ревизии через годы).

### 3.5 Документация и лицензия
- `README.md` (сейчас 6 байт) → реальный: что это, установка, как запустить серии, как воспроизвести результаты диплома, где смотреть таблицы/графики, легенда метрик (D, M_cum, pi_chg) и алгоритмов.
- `LICENSE` (например, MIT - или по требованиям вуза) и `CITATION.cff`, если будет публикация/защита.

---

## 4. P2 - качество кода (полировка)

- **ruff: 14 замечаний** - 5× неоднозначные имена (`E741`: `l`/`O`/`I`), 5× неиспользуемые переменные (`F841`), 3× неиспользуемые импорты (`F401`), 1× lambda-присваивание. 3 авто-фикса: `ruff check --fix`; имена переименовать руками.
- **mypy: 15 ошибок типов** в 7 файлах (несовместимость `None`/`ndarray` в `ach.py`, `experiment.py`; недостающие аннотации). Добавить аннотации, инициализировать массивы вместо `None`, включить mypy в CI.
- **Сложность (radon):** `run_experiment` - **D (CC=26)**, `ACH._rebalance` - C(19), `DynamicR.step` - C(17). Разнести `run_experiment` на функции (setup → шаг симуляции → запись метрик); так его станет можно юнит-тестировать.
- **`.pre-commit-config.yaml`** (ruff, ruff-format, mypy) - чтобы стиль и типы держались автоматически.
- **`Makefile`/`tasks`**: `make setup|test|lint|run|reproduce` - единые точки входа.
- Убрать из истории трекинг `*.pyc` (уже частично сделано в коммите 590ee06; проверить, что `__pycache__` нигде не закоммичен).

---

## 5. Сводный приоритет

| # | Действие | Приоритет | Усилие | Влияние |
|---|---|---|---|---|
| 1 | Влить фикс BoundedLoads, пересчитать результаты, обновить числа в дипломе | 🔴 P0 | M | Очень высокое (корректность выводов) |
| 2 | Тесты на `metrics.compute_D`, `run_experiment`, базлайны, детерминизм | 🔴 P0 | M | Очень высокое |
| 3 | Поправка на множественные сравнения (Holm/BH) | 🔴 P0 | S | Высокое (статистическая честность) |
| 4 | `pyproject.toml` + `conftest.py` (убрать sys.path-хаки) | 🟠 P1 | S | Высокое |
| 5 | CI на `main` (ruff+mypy+pytest+coverage, матрица 3.10–3.12) | 🟠 P1 | S | Высокое |
| 6 | Провенанс в результатах + пины/лок зависимостей + Docker/conda | 🟠 P1 | M | Высокое (воспроизводимость) |
| 7 | Настоящий `README.md` + `LICENSE` + `CITATION.cff` | 🟠 P1 | S | Среднее |
| 8 | Поднять покрытие до ≥70% (кластер, шум, генератор, скрипты) | 🟠 P1 | M | Высокое |
| 9 | Свести ветки, удалить отработавшие | 🟠 P1 | S | Среднее |
| 10 | ruff --fix + переименования, аннотации типов, рефактор `run_experiment` | 🟡 P2 | M | Среднее |
| 11 | pre-commit + Makefile | 🟡 P2 | S | Среднее |

**Порядок одним предложением:** сначала вернуть научную корректность (1–3), затем сделать репозиторий устанавливаемым и поставить CI (4–5), закрыть воспроизводимость и документацию (6–7), добить покрытие и полировку (8–11).

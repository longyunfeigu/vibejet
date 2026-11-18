#!/usr/bin/env python3
"""把这次改动真跑起来，用证据证明它能用。

    verify.py run   [--level auto|none|api|ui] [--base REF] [--keep]   便宜检查 → 起环境 → 冒烟 → 关环境
    verify.py up    [--level api|ui]                                    只起环境（vj-work 起一次、多个切片共用）
    verify.py smoke [--level api|ui]                                    对已起的环境跑冒烟
    verify.py down                                                      停服务、删容器
    verify.py status | env                                              查看环境 / 打印给 AutoTest 用的 export 行

环境是隔离的：独立的 postgres 容器（tmpfs，每次干净）、随机空闲端口上的后端和前端，
不读写本机已有的容器和 8010 / 5173 端口。状态和日志写在 <repo>/.vj/verify/（已 gitignore）。
每次 run / smoke 都把逐步结果写进 .vj/verify/report.md，最后一行是可以直接贴进 commit 的
`Verified:` trailer。退出码：0 全过；1 有步骤失败；2 用法或前置条件错误。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import secrets
import shlex
import shutil
import signal
import socket
import subprocess  # nosec B404 - 本脚本的职责就是编排本地命令
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

LEVELS = ("none", "api", "ui")
PG_IMAGE = "postgres:15-alpine"
PG_USER = PG_PASSWORD = PG_DB = "verify"  # nosec B105 - 一次性 tmpfs 测试库，只监听 127.0.0.1
E2E_ENV = "verify"
E2E_USER = "e2e-fixture-user-a"
E2E_EMAIL = "e2e-fixture-user-a@example.com"
BOOT_TIMEOUT_S = 90
# uvicorn --reload 只监视源码目录；监视整个 backend/ 会把 .venv 也扫进去
RELOAD_DIRS = ("api", "application", "core", "domain", "infrastructure", "shared")


# ── 改动 → 档位 ────────────────────────────────────────────────────────────


def classify(path: str) -> str:
    """一个改动文件需要哪一档运行验证。"""
    if path.endswith(".md") or path.startswith(("docs/", ".agents/", ".claude/", ".github/")):
        return "none"
    if path.startswith("backend/"):
        return "api"
    return "ui"


def pick_level(paths: list[str]) -> str:
    """没有改动时按最全的 ui 档验，宁可多验不漏验。"""
    if not paths:
        return "ui"
    return max((classify(p) for p in paths), key=LEVELS.index)


def cheap_checks(paths: list[str]) -> list[tuple[str, str, str]]:
    """(名字, 工作目录, 命令)。按改动面挑，先跑最便宜的。"""
    if not paths:
        touched = {"backend", "frontend"}
    else:  # 纯文档改动（如 backend/README.md）不值得跑整套测试
        touched = {p.split("/", 1)[0] for p in paths if classify(p) != "none"}
    checks: list[tuple[str, str, str]] = []
    if "backend" in touched:
        checks += [
            ("后端依赖方向", "backend", "uv run --no-sync lint-imports"),
            ("后端测试", "backend", "uv run --no-sync pytest -q -x -p no:cacheprovider"),
        ]
    if "frontend" in touched:
        checks += [
            ("前端类型检查", "frontend", "pnpm -s typecheck"),
            ("前端 lint", "frontend", "pnpm -s lint"),
            ("前端单测", "frontend", "pnpm -s test"),
        ]
    if "AutoTest" in touched:
        checks += [
            ("AutoTest 类型检查", "AutoTest", "npm run -s typecheck"),
            ("AutoTest BDD 规范", "AutoTest", "npm run -s lint:bdd"),
        ]
    return checks


# ── 仓库与状态 ─────────────────────────────────────────────────────────────


def repo_root() -> Path:
    out = subprocess.run(  # nosec B603 B607 - 固定的 git 命令
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        sys.exit("verify: 不在 git 仓库里")
    return Path(out.stdout.strip())


def changed_paths(root: Path, base: str | None) -> list[str]:
    def git(*args: str) -> list[str]:
        out = subprocess.run(  # nosec B603 B607 - 固定的 git 命令
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
        return [line for line in out.stdout.splitlines() if line]

    paths = set(git("diff", "--name-only", "HEAD")) | set(
        git("ls-files", "--others", "--exclude-standard")
    )
    if base:
        paths |= set(git("diff", "--name-only", f"{base}...HEAD"))
    return sorted(paths)


def state_dir(root: Path) -> Path:
    d = root / ".vj" / "verify"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_state(root: Path) -> dict | None:
    f = state_dir(root) / "state.json"
    return json.loads(f.read_text()) if f.exists() else None


def save_state(root: Path, state: dict) -> None:
    (state_dir(root) / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))


def container_name(root: Path) -> str:
    # 每个 worktree 一个容器名，并行的 worktree 互不干扰
    return f"vj-verify-{hashlib.sha1(str(root).encode(), usedforsecurity=False).hexdigest()[:8]}"


# ── 步骤记录 ───────────────────────────────────────────────────────────────


@dataclass
class Step:
    name: str
    ok: bool
    seconds: float
    detail: str = ""


@dataclass
class Report:
    steps: list[Step] = field(default_factory=list)

    def add(self, name: str, ok: bool, started: float, detail: str = "") -> bool:
        step = Step(name, ok, time.monotonic() - started, detail)
        self.steps.append(step)
        mark = "✓" if ok else "✗"
        print(
            f"  {mark} {name} ({step.seconds:.1f}s){' — ' + detail if detail else ''}", flush=True
        )
        return ok

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


def write_report(root: Path, report: Report, level: str, paths: list[str]) -> str:
    stamp = trailer(report, level)
    lines = [
        "# verify 报告",
        "",
        f"- 时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 档位：{level}（改动文件 {len(paths)} 个）",
        f"- 结果：{'通过' if report.ok else '失败'}",
        "",
        "| 步骤 | 结果 | 耗时 | 说明 |",
        "|------|------|------|------|",
    ]
    for s in report.steps:
        detail = s.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {s.name} | {'通过' if s.ok else '失败'} | {s.seconds:.1f}s | {detail} |")
    lines += ["", "commit trailer：", "", f"    {stamp}", ""]
    (state_dir(root) / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return stamp


def trailer(report: Report, level: str) -> str:
    if not report.ok:
        failed = next(s.name for s in report.steps if not s.ok)
        return f"Verified: none (verify 失败于：{failed})"
    return {"none": "Verified: checks", "api": "Verified: smoke-api", "ui": "Verified: smoke-ui"}[
        level
    ]


# ── 小工具 ─────────────────────────────────────────────────────────────────


def free_port() -> int:
    """在 20000-39999 里找空闲端口。不用系统分配（bind 0）：那会落在临时端口段，
    释放后到服务真正绑定之前，常被本机的出站连接抢走（实测 docker 报 address already in use）。"""
    for _ in range(100):
        port = 20000 + secrets.randbelow(20000)
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("20000-39999 里找不到空闲端口")


def sh(cmd: str, cwd: Path, env: dict | None = None, log: Path | None = None) -> tuple[bool, str]:
    """跑一条命令（不经 shell）；失败时返回输出末尾，方便直接定位。"""
    out = subprocess.run(  # nosec B603 - 命令都是本脚本里写死的
        shlex.split(cmd), cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    text = out.stdout + out.stderr
    if log:
        log.write_text(text, encoding="utf-8")
    return out.returncode == 0, tail(text)


def tail(text: str, n: int = 12) -> str:
    """输出末尾几行；真正的原因常在更前面，把第一条 Error 行提到最前。"""
    lines = text.strip().splitlines()
    first_error = next((line.strip() for line in lines if "Error:" in line), "")
    last = "\n".join(lines[-n:])
    return f"{first_error}\n{last}" if first_error and first_error not in last else last


def http(method: str, url: str, body: dict | None = None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(
            req, timeout=10
        ) as resp:  # nosec B310 - 只请求本脚本拼出的 http://127.0.0.1
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw.startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except (urllib.error.URLError, OSError) as e:
        return 0, str(e)


def envelope_data(body: object) -> dict:
    """取响应信封里的 data；接口坏了时 data 可能是 null、字符串或整个不是 JSON，一律当空，让步骤判失败而不是脚本崩。"""
    data = body.get("data") if isinstance(body, dict) else None
    return data if isinstance(data, dict) else {}


def wait_until(probe, proc: subprocess.Popen | None, timeout: float) -> bool:
    """轮询一个可观测状态（端口应答、pg_isready），进程提前退出就立刻判失败。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        if probe():
            return True
        time.sleep(0.5)
    return False


def spawn(cmd: list[str], cwd: Path, env: dict, log: Path) -> subprocess.Popen:
    # 新会话：down 时按进程组整组杀掉（uv / pnpm 会再派子进程）
    return subprocess.Popen(  # nosec B603 - 命令都是本脚本里写死的
        cmd,
        cwd=cwd,
        env=env,
        stdout=log.open("w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


# 进程命令行里必须出现的词：PID 会被系统复用，只认得出是自己起的服务才算活着、才去杀
SERVICE_MARKERS = {"backend": "uvicorn", "frontend": "vite"}


def alive(service: str, pid: int) -> bool:
    out = subprocess.run(  # nosec B603 B607 - 固定的 ps 命令
        ["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, check=False
    )
    return SERVICE_MARKERS[service] in out.stdout


# ── up / smoke / down ──────────────────────────────────────────────────────


def ensure_deps(root: Path, level: str, report: Report) -> bool:
    t = time.monotonic()
    backend, frontend = root / "backend", root / "frontend"
    if not (backend / ".venv").exists():
        ok, out = sh(
            "uv sync --all-extras --locked --python 3.11", backend
        )  # 和 CI 一致，测试要用到可选依赖
        if not ok:
            return report.add("安装后端依赖", False, t, out)
    # Apple Silicon：uv.lock 里 greenlet 的平台条件不含 arm64，缺它 alembic 跑不了
    if platform.machine() == "arm64":
        ok, _ = sh("uv run --no-sync python -c 'import greenlet'", backend)
        if not ok:
            ok, out = sh("uv pip install greenlet", backend)
            if not ok:
                return report.add("安装 greenlet", False, t, out)
    if level == "ui":
        if not (frontend / "node_modules").exists():
            ok, out = sh("pnpm install --frozen-lockfile", frontend)
            if not ok:
                return report.add("安装前端依赖", False, t, out)
        autotest = root / "AutoTest"
        if not (autotest / "node_modules").exists():
            ok, out = sh("npm install", autotest)
            if not ok:
                return report.add("安装 AutoTest 依赖", False, t, out)
        # 已装时秒回；Playwright 升级后浏览器版本号会变，不装 globalSetup 直接起不来
        ok, out = sh("npx playwright install chromium", autotest)
        if not ok:
            return report.add("安装 Playwright 浏览器", False, t, out)
    return report.add("依赖就绪", True, t)


def up(root: Path, level: str, report: Report, check_deps: bool = True) -> dict | None:
    state = load_state(root)
    if (
        state
        and all(alive(k, p) for k, p in state["pids"].items())
        and (level != "ui" or "frontend" in state["pids"])
    ):
        print(f"verify: 复用已起的环境 {state['backend_url']}", flush=True)
        return state
    if state:
        down(root, quiet=True)
    if not shutil.which("docker"):
        report.add("docker 可用", False, time.monotonic(), "找不到 docker 命令")
        return None
    if check_deps and not ensure_deps(root, level, report):
        return None

    sd = state_dir(root)
    name = container_name(root)
    pg_port, be_port = free_port(), free_port()
    state = {
        "container": name,
        "pids": {},
        "level": level,
        "logs": str(sd),
        # 测试账号的密码每次随机；AutoTest 的 globalSetup 和 smoke 都会在账号不存在时先注册
        "password": secrets.token_urlsafe(12),
    }
    save_state(root, state)

    # 1. postgres：tmpfs 数据目录，每次都是干净库；端口在检查和绑定之间仍可能被抢，被抢就换一个
    t = time.monotonic()
    for _ in range(3):
        ok, out = sh(
            f"docker run -d --name {name} -e POSTGRES_USER={PG_USER} -e POSTGRES_PASSWORD={PG_PASSWORD} "
            f"-e POSTGRES_DB={PG_DB} -p 127.0.0.1:{pg_port}:5432 --tmpfs /var/lib/postgresql/data {PG_IMAGE}",
            root,
        )
        if ok or "address already in use" not in out:
            break
        sh(f"docker rm -f {name}", root)
        pg_port = free_port()
    # initdb 期间的临时服务只听 unix socket，所以走 TCP 探测才代表真正可连
    ready = ok and wait_until(
        lambda: sh(f"docker exec {name} pg_isready -h 127.0.0.1 -U {PG_USER}", root)[0],
        None,
        BOOT_TIMEOUT_S,
    )
    if not report.add("数据库", ready, t, f"容器 {name}，端口 {pg_port}" if ready else out):
        return None

    state["backend_env"] = {
        "SECRET_KEY": secrets.token_hex(32),
        "DATABASE__URL": f"postgresql+asyncpg://{PG_USER}:{PG_PASSWORD}@127.0.0.1:{pg_port}/{PG_DB}",
        "STORAGE__LOCAL_BASE_PATH": str(sd / "storage"),
    }
    save_state(root, state)
    env = {**os.environ, **state["backend_env"]}
    backend = root / "backend"

    # 2. 翻译 + 迁移
    t = time.monotonic()
    ok, out = migrate(root, state)
    if not report.add("翻译编译 + 迁移", ok, t, "" if ok else out):
        return None

    # 3. 后端
    t = time.monotonic()
    proc = spawn(
        [
            "uv",
            "run",
            "--no-sync",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(be_port),
            # 环境会被多个切片共用：改了后端代码要立刻生效，否则冒烟测的是起环境时的旧代码
            "--reload",
            *[arg for d in RELOAD_DIRS for arg in ("--reload-dir", d)],
        ],
        backend,
        env,
        sd / "backend.log",
    )
    state["pids"]["backend"] = proc.pid
    state["backend_url"] = f"http://127.0.0.1:{be_port}"
    save_state(root, state)
    ok = wait_until(
        lambda: http("GET", f"{state['backend_url']}/health/live")[0] == 200, proc, BOOT_TIMEOUT_S
    )
    detail = state["backend_url"] if ok else tail((sd / "backend.log").read_text())
    if not report.add("后端启动", ok, t, detail):
        return None

    # 4. 前端：API_PROXY_TARGET 只改 dev 代理目标；设 VITE_API_URL 会让浏览器直连后端撞 CORS
    if level == "ui":
        fe_port = free_port()
        t = time.monotonic()
        proc = spawn(
            ["pnpm", "exec", "vite", "--host", "127.0.0.1", "--port", str(fe_port), "--strictPort"],
            root / "frontend",
            {**os.environ, "API_PROXY_TARGET": state["backend_url"]},
            sd / "frontend.log",
        )
        state["pids"]["frontend"] = proc.pid
        state["frontend_url"] = f"http://127.0.0.1:{fe_port}"
        save_state(root, state)
        ok = wait_until(
            lambda: http("GET", f"{state['frontend_url']}/api/v1/auth/me")[0] == 401,
            proc,
            BOOT_TIMEOUT_S,
        )
        detail = (
            f"{state['frontend_url']}（代理已连到后端）"
            if ok
            else tail((sd / "frontend.log").read_text())
        )
        if not report.add("前端启动", ok, t, detail):
            return None

    state["level"] = level
    save_state(root, state)
    return state


def migrate(root: Path, state: dict) -> tuple[bool, str]:
    """翻译编译 + 迁移，都是幂等的；smoke 前再跑一次，把环境起来之后新加的迁移也应用上。"""
    backend, env = root / "backend", {**os.environ, **state["backend_env"]}
    # 不编译翻译，接口返回原始 key（如 auth.password.invalid）
    ok, out = sh("uv run --no-sync pybabel compile -d locales/", backend, env)
    if ok:
        log = state_dir(root) / "alembic.log"
        ok, out = sh("uv run --no-sync alembic upgrade head", backend, env, log)
    return ok, out


def smoke(root: Path, state: dict, level: str, report: Report) -> None:
    base = state["backend_url"]
    sd = state_dir(root)

    t = time.monotonic()
    ok, out = migrate(root, state)
    if not report.add("应用最新迁移", ok, t, "" if ok else out):
        return

    t = time.monotonic()
    code, _ = http("GET", f"{base}/health/live")
    if not report.add("健康检查 /health/live", code == 200, t, f"HTTP {code}"):
        return

    # 每次起环境都是空库：注册 → 登录 → 带 token 读自己 → 读一个按归属过滤的列表
    password = state["password"]
    t = time.monotonic()
    code, body = http(
        "POST",
        f"{base}/api/v1/auth/register",
        {"username": E2E_USER, "email": E2E_EMAIL, "password": password},
    )
    if not report.add(
        "注册",
        code in (200, 201, 409),
        t,
        f"HTTP {code}" + ("" if code < 300 or code == 409 else f" {body}"),
    ):
        return
    t = time.monotonic()
    code, body = http(
        "POST", f"{base}/api/v1/auth/login", {"username": E2E_USER, "password": password}
    )
    token = envelope_data(body).get("access_token")
    if not report.add(
        "登录", code == 200 and bool(token), t, f"HTTP {code}" + ("" if token else f" {body}")
    ):
        return
    t = time.monotonic()
    code, body = http("GET", f"{base}/api/v1/auth/me", token=token)
    who = envelope_data(body).get("username")
    if not report.add(
        "带 token 读当前用户", code == 200 and who == E2E_USER, t, f"HTTP {code}，用户 {who}"
    ):
        return
    t = time.monotonic()
    code, body = http("GET", f"{base}/api/v1/conversations", token=token)
    if not report.add("读归属列表 /conversations", code == 200, t, f"HTTP {code}"):
        return

    if level != "ui":
        return

    # 浏览器：AutoTest 里打 @smoke 的场景，跑在这次起的前端上
    autotest = root / "AutoTest"
    # 环境每次重建（新库、新 SECRET_KEY），上次缓存的登录态必然失效
    (autotest / "config" / f"auth-state-{E2E_ENV}.json").unlink(missing_ok=True)
    env = {**os.environ, "HEADLESS": "true", "E2E_RUNNER": "1", **autotest_env(state)}
    t = time.monotonic()
    ok, out = sh("./core/runner/run-bdd.sh smoke " + E2E_ENV, autotest, env, sd / "autotest.log")
    if ok:
        detail = f"报告 AutoTest/report/test-reports-{E2E_ENV}/playwright/index.html"
    else:
        detail = (
            f"{out}\n失败截图在 AutoTest/report/test-artifacts/，"
            f"失败用例 CSV 在 AutoTest/report/test-results/"
        )
    if not report.add("浏览器冒烟（AutoTest @smoke）", ok, t, detail):
        return

    # 成功也留一张图：人看一眼就知道页面真的出来了
    t = time.monotonic()
    shot = sd / "home.png"
    ok, out = sh(
        f"npx playwright screenshot --load-storage config/auth-state-{E2E_ENV}.json "
        # 等应用外壳的 <main>，不等首页内容：首页是占位页，下游会换掉
        f"--wait-for-selector main --viewport-size 1440,900 {state['frontend_url']}/ {shot}",
        autotest,
    )
    report.add("首页截图", ok and shot.exists(), t, str(shot.relative_to(root)) if ok else out)


def autotest_env(state: dict) -> dict[str, str]:
    """AutoTest 的 env-config.ts 认这组变量，优先于 environments.json。"""
    return {
        "E2E_ENV": E2E_ENV,
        "E2E_BASE_URL": state["frontend_url"],
        "E2E_USERNAME": E2E_USER,
        "E2E_PASSWORD": state["password"],
        "E2E_EMAIL": E2E_EMAIL,
    }


def down(root: Path, quiet: bool = False) -> None:
    state = load_state(root)
    if not state:
        if not quiet:
            print("verify: 没有在运行的环境")
        return
    for service, pid in state["pids"].items():
        if alive(service, pid):
            with contextlib.suppress(OSError):
                os.killpg(pid, signal.SIGTERM)
    subprocess.run(  # nosec B603 B607 - 固定的 docker 命令
        ["docker", "rm", "-f", state["container"]], capture_output=True, check=False
    )
    (state_dir(root) / "state.json").unlink(missing_ok=True)
    if not quiet:
        print(f"verify: 已停止服务、删除容器 {state['container']}（日志留在 {state['logs']}）")


# ── 入口 ───────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--level", choices=("auto", *LEVELS), default="auto")
    p_run.add_argument("--base", help="额外把 BASE...HEAD 的已提交改动算进来（如 main）")
    p_run.add_argument("--keep", action="store_true", help="跑完不关环境，留给人亲手试")
    p_up = sub.add_parser("up")
    p_up.add_argument("--level", choices=("api", "ui"), default="ui")
    p_smoke = sub.add_parser("smoke")
    p_smoke.add_argument("--level", choices=("api", "ui"))
    sub.add_parser("down")
    sub.add_parser("status")
    sub.add_parser("env", help="打印 export 行，让 AutoTest 直接打这次起的环境")
    args = parser.parse_args()

    root = repo_root()
    report = Report()

    if args.cmd == "down":
        down(root)
        return 0
    if args.cmd == "status":
        state = load_state(root)
        if not state:
            print("verify: 没有在运行的环境")
            return 0
        state["alive"] = {k: alive(k, p) for k, p in state["pids"].items()}
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "env":
        state = load_state(root)
        if not state or "frontend_url" not in state:
            print("verify: 没有带前端的环境，先跑 verify.py up --level ui", file=sys.stderr)
            return 2
        for key, value in autotest_env(state).items():
            print(f"export {key}={shlex.quote(value)}")
        return 0

    if args.cmd == "up":
        state = up(root, args.level, report)
        if not state:
            down(root, quiet=True)  # 起到一半失败，不留半套环境
        write_report(root, report, args.level, [])
        return 0 if state else 1

    if args.cmd == "smoke":
        state = load_state(root)
        if not state:
            print("verify: 环境没起，先跑 verify.py up", file=sys.stderr)
            return 2
        level = args.level or state["level"]
        if level == "ui" and "frontend_url" not in state:
            print("verify: 环境是 api 档起的，没有前端；用 up --level ui 重起", file=sys.stderr)
            return 2
        smoke(root, state, level, report)
        print(f"\n{write_report(root, report, level, [])}")
        return 0 if report.ok else 1

    # run
    paths = changed_paths(root, args.base)
    level = pick_level(paths) if args.level == "auto" else args.level
    print(f"verify: 改动文件 {len(paths)} 个 → 档位 {level}", flush=True)

    # 依赖先装好：后端检查用 uv run --no-sync、AutoTest 检查用 npm run，都不会自己装
    if level != "none" and not ensure_deps(root, level, report):
        paths_checks: list[tuple[str, str, str]] = []
    else:
        paths_checks = cheap_checks(paths)

    for name, cwd, cmd in paths_checks:
        t = time.monotonic()
        ok, out = sh(cmd, root / cwd, log=state_dir(root) / f"check-{name}.log")
        if not report.add(name, ok, t, "" if ok else out):
            break

    if report.ok and level != "none":
        down(root, quiet=True)  # run 每次从干净环境开始，不复用之前 --keep 留下的
        try:
            state = up(root, level, report, check_deps=False)
            if state:
                smoke(root, state, level, report)
        finally:
            if not args.keep:
                down(root, quiet=True)
            elif load_state(root):
                s = load_state(root)
                print(
                    f"\nverify: 环境保留中 → 前端 {s.get('frontend_url', '-')}，后端 {s['backend_url']}；"
                    f"用完跑 verify.py down"
                )

    stamp = write_report(root, report, level, paths)
    print(f"\n报告：{(state_dir(root) / 'report.md').relative_to(root)}\n{stamp}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

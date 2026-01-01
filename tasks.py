"""Scripts for managing the project."""

import shutil
import sys
import time

from invoke import Collection, Context, task


def get_allowed_doc_languages():
    build_docs_file_name = "scripts/build-docs.sh"
    try:
        with open(build_docs_file_name) as f:
            for line in f:
                if "for lang in" in line:
                    langs = line.split("in")[1].strip().split(";")[0].split()
                    return [lang.strip() for lang in langs]
    except FileNotFoundError:
        print(f"No {build_docs_file_name} file found")
    return ["en", "bg", "de", "es", "fr", "ru"]  # default


ALLOWED_DOC_LANGUAGES = get_allowed_doc_languages()
ALLOWED_VERSION_TYPES = ["release", "bug", "feature"]


@task
def version(_c: Context):
    """Show the current version."""
    with open("lexiflux/__about__.py") as f:
        version_line = f.readline()
        version_num = version_line.split('"')[1]
        print(version_num)
        return version_num


def ver_task_factory(version_type: str):
    @task
    def ver(c: Context):
        """Bump the version."""
        c.run(f"./scripts/verup.sh {version_type}")

    return ver


def docs_task_factory(language: str):
    @task
    def docs(c: Context):
        """Docs preview for the language specified."""
        c.run("open -a 'Google Chrome' http://127.0.0.1:8000/")
        c.run(f"scripts/docs-render-config.sh {language}")
        if language != "en":
            shutil.rmtree(f"./docs/src/{language}/images", ignore_errors=True)
            shutil.copytree("./docs/src/en/images", f"./docs/src/{language}/images")
        c.run("mkdocs serve -f docs/_mkdocs.yml")

    return docs


@task
def shell(c: Context):
    """Django shell"""
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage shell")


@task
def jupyter(c: Context):
    """Run Jupyter Notebook"""
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage shell_plus --notebook")


@task
def migrate(c: Context):
    """Migrate DB to current models"""
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage makemigrations lexiflux")
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage migrate")


@task
def pages(c: Context):
    """Create random book with random pages"""
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage add-pages")


@task
def alisa(c: Context):
    """Import Alisa u zemlji cuda"""
    c.run(
        r"""LEXIFLUX_SKIP_AUTH=true ./manage.py"""
        r""" import-text "${HOME}/books/Lewis Carroll/Alice's Adventures """
        r"""in Wonderland (96)/Alice's Adventures in Wonderland - Lewis Carroll.txt" """,
    )


@task
def alice(c: Context):
    """Import Alice's Adventures in Wonderland from Gutenberg Project"""
    c.run(
        r"""LEXIFLUX_SKIP_AUTH=true ./manage.py"""
        r""" import-url "https://www.gutenberg.org/cache/epub/11/pg11-images.html" """
        r""" --cleaning-level minimal --public""",
    )


@task
def kill_db(c: Context):
    """KILL Database"""
    c.run("rm -f db.sqlite3")


@task
def admin(c: Context):
    """Create admin"""
    c.run(
        "DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser "
        "--username admin --email admin@example.com --noinput",
    )


@task
def user(c: Context):
    """Create default user for auto-login"""
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage default-user")


@task(kill_db, migrate, admin, user, alisa)
def init_db(c: Context):
    """KILL Database and reinit new one"""


@task
def run(c: Context):
    """Run local server"""
    c.run("LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage runserver 0.0.0.0:8000")


@task
def runssl(c: Context):
    """Run local SSL server in auto-login mode"""
    c.run(
        "LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=true ./manage runserver_plus 0.0.0.0:8000 "
        "--cert-file ssl_certs/localhost.crt --key-file ssl_certs/localhost.key",
    )


@task
def runcloud(c: Context):
    """Run local SSL server in multi-user mode"""
    c.run(
        "LEXIFLUX_ENV=local LEXIFLUX_SKIP_AUTH=false ./manage runserver_plus 0.0.0.0:8000 "
        "--cert-file ssl_certs/localhost.crt --key-file ssl_certs/localhost.key",
    )


@task
def compile_requirements(c: Context):
    "Convert requirements.in to requirements.txt, requirements.dev.txt, and requirements.koyeb.txt."

    start_time = int(time.time())

    c.run(
        "uv pip compile requirements.in --output-file=requirements.txt --upgrade",
    )  # --refresh-package

    reqs_time = int(time.time())

    c.run("uv pip compile requirements.dev.in --output-file=requirements.dev.txt --upgrade")

    dev_time = int(time.time())

    c.run("uv pip compile requirements.koyeb.in --output-file=requirements.koyeb.txt --upgrade")

    end_time = int(time.time())

    print(f"Req's compilation time: {reqs_time - start_time} seconds")
    print(f"Req's dev compilation time: {dev_time - reqs_time} seconds")
    print(f"Req's koyeb compilation time: {end_time - dev_time} seconds")
    print(f"Total execution time: {end_time - start_time} seconds")


@task(pre=[compile_requirements])
def reqs(c: Context):
    """Upgrade requirements including pre-commit."""
    c.run("pre-commit autoupdate")
    c.run("uv pip install -r requirements.dev.txt")


@task
def sql(c: Context):
    """sqlite3"""
    c.run("sqlite3 db.sqlite3 -header")


@task
def get_books(c: Context):
    """Select books from DB"""
    c.run('sqlite3 db.sqlite3 "SELECT * FROM lexiflux_book;"')


@task
def buildjs(c: Context):
    """Bundle and minify JavaScript in Django static folder"""
    c.run("npm run build")


@task(help={"k": "Pytest filter expression (-k)"})
def test(c: Context, k=None):
    """Run tests and create Allure report."""
    c.run("rm -rf allure-results")

    # Build the pytest command with the filter if provided
    pytest_cmd = "python -m pytest --alluredir=allure-results"
    if k:
        pytest_cmd += f" -k {k}"
    pytest_cmd += " tests"

    c.run(pytest_cmd, warn=True)

    # c.run("ALLURE_LABEL_EPIC='viewport.ts' npm test", warn=True)
    c.run(
        "docker compose run --rm -i allure allure generate /allure-results "
        "-o /allure-report --clean",
    )
    c.run("docker compose restart allure")
    c.run("open -a 'Google Chrome' http://localhost:8800")


@task
def selenium(c: Context):
    """Run selenium tests and create Allure report"""
    c.run("rm -rf allure-results")
    c.run("python -m pytest --alluredir=allure-results tests -m selenium -s -vv", warn=True)
    c.run(
        "docker compose run --rm allure allure generate /allure-results -o /allure-report --clean",
    )
    c.run("docker compose restart allure")
    c.run("open -a 'Google Chrome' http://localhost:8800/index.html#behaviors")


@task
def keygen(c: Context):
    """Generate SSL key and cert for localhost"""
    c.run("mkdir -p ssl_certs")
    c.run(
        "openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
        "-keyout ssl_certs/localhost.key -out ssl_certs/localhost.crt",
    )


@task
def mkcert(c: Context):
    """Generate SSL cert with mkcert"""
    c.run("mkdir -p ssl_certs")
    c.run(
        "mkcert -cert-file ssl_certs/localhost.crt "
        "-key-file ssl_certs/localhost.key lexiflux.ai localhost 127.0.0.1",
    )


@task
def docker(c: Context):
    """Build docker image"""
    c.run("docker build -t lexiflux:latest -f docker/Dockerfile .")


@task
def rundocker(c: Context):
    """Run built docker image"""
    c.run("docker run --rm -p 8080:8000 lexiflux:latest")


@task
def uv(c: Context):
    """Install or upgrade uv."""
    c.run("curl -LsSf https://astral.sh/uv/install.sh | sh")


@task
def pre(c):
    """Run pre-commit checks"""
    c.run("pre-commit run --verbose --all-files")


@task
def test_koyeb(c: Context):
    """Test koyeb configuration in separate venv"""
    # Create separate venv for koyeb testing
    c.run("uv venv .venv-koyeb", warn=True)
    # Install koyeb requirements
    c.run("source .venv-koyeb/bin/activate && uv pip install -r requirements.koyeb.txt")
    # Test Django configuration with koyeb settings
    c.run(
        "source .venv-koyeb/bin/activate && "
        "LEXIFLUX_ENV=koyeb "
        "SECRET_KEY=test-secret-key "
        "DATABASE_URL=sqlite:///test-koyeb.db "
        "./manage check --deploy",
    )
    # Test collectstatic
    c.run(
        "source .venv-koyeb/bin/activate && "
        "LEXIFLUX_ENV=koyeb "
        "SECRET_KEY=test-secret-key "
        "DATABASE_URL=sqlite:///test-koyeb.db "
        "./manage collectstatic --noinput",
    )
    print("Koyeb configuration test passed!")


namespace = Collection.from_module(sys.modules[__name__])
for name in ALLOWED_VERSION_TYPES:
    namespace.add_task(ver_task_factory(name), name=f"ver-{name}")  # type: ignore[bad-argument-type]
for name in ALLOWED_DOC_LANGUAGES:
    namespace.add_task(docs_task_factory(name), name=f"docs-{name}")  # type: ignore[bad-argument-type]

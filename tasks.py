"""Scripts for managing the project."""
import shutil
import sys

from invoke import task, Context, Collection
import subprocess


def get_allowed_doc_languages():
    build_docs_file_name = "scripts/build-docs.sh"
    try:
        with open(build_docs_file_name, "r") as f:
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
def version(c: Context):
    """Show the current version."""
    with open("lexiflux/__about__.py", "r") as f:
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
        c.run("open -a 'Google Chrome' http://127.0.0.1:8000/lexiflux/")
        c.run(f"scripts/docs-render-config.sh {language}")
        if language != "en":
            shutil.rmtree(f"./docs/src/{language}/images", ignore_errors=True)
            shutil.copytree("./docs/src/en/images", f"./docs/src/{language}/images")
        c.run("mkdocs serve -f docs/_mkdocs.yml")

    return docs


@task
def shell(c: Context):
    """Django shell"""
    c.run("./manage shell")

@task
def jupyter(c: Context):
    """Run Jupyter Notebook"""
    c.run("./manage shell_plus --notebook")


@task
def migrate(c: Context):
    """Migrate DB to current models"""
    c.run("./manage makemigrations lexiflux")
    c.run("./manage migrate")


@task
def pages(c: Context):
    """Create random book with random pages"""
    c.run("./manage add-pages")


@task
def alisa(c: Context):
    """Import Alisa u zemlji cuda"""
    c.run(
        r"""./manage.py import-text "${HOME}/books/Lewis Carroll/Alice's Adventures """
        r"""in Wonderland (96)/Alice's Adventures in Wonderland - Lewis Carroll.txt" """
    )


@task
def kill_db(c: Context):
    """KILL Database"""
    c.run("rm -f db.sqlite3")


@task
def admin(c: Context):
    """Create admin"""
    c.run(
        "DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser --username admin --email admin@example.com --noinput"
    )


@task
def user(c: Context):
    """Create default user for auto-login"""
    c.run("./manage default-user")


@task(kill_db, migrate, admin, user, alisa)
def init_db(c: Context):
    """KILL Database and reinit new one"""
    pass


@task
def run(c: Context):
    """Run local server"""
    c.run("LEXIFLUX_SKIP_AUTH=true ./manage runserver")


@task
def runssl(c: Context):
    """Run local SSL server"""
    c.run(
        "LEXIFLUX_SKIP_AUTH=true ./manage runserver_plus 0.0.0.0:8000 "
        "--cert-file ssl_certs/localhost.crt --key-file ssl_certs/localhost.key"
    )


@task
def compile_requirements(c: Context):
    "Convert requirements.in to requirements.txt and requirements.dev.txt."
    start_time = subprocess.check_output(["date", "+%s"]).decode().strip()
    c.run("uv pip compile requirements.in --output-file=requirements.txt --upgrade")
    reqs_time = subprocess.check_output(["date", "+%s"]).decode().strip()
    c.run("uv pip compile requirements.dev.in --output-file=requirements.dev.txt --upgrade")
    end_time = subprocess.check_output(["date", "+%s"]).decode().strip()
    print(f"Req's compilation time: {int(reqs_time) - int(start_time)} seconds")
    print(f"Req's dev compilation time: {int(end_time) - int(reqs_time)} seconds")
    print(f"Total execution time: {int(end_time) - int(start_time)} seconds")


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


@task
def test(c: Context):
    """Run tests and create Allure report"""
    c.run("rm -rf allure-results")
    c.run("python -m pytest --alluredir=allure-results tests", warn=True)
    c.run("ALLURE_LABEL_EPIC='viewport.ts' npm test", warn=True)
    c.run(
        "docker compose run --rm -it allure allure generate /allure-results "
        "-o /allure-report --clean"
    )
    c.run("docker compose restart allure")
    c.run("open -a 'Google Chrome' http://localhost:8800")


@task
def selenium(c: Context):
    """Run selenium tests and create Allure report"""
    c.run("rm -rf allure-results")
    c.run("python -m pytest --alluredir=allure-results tests -m selenium -s -vv", warn=True)
    c.run(
        "docker compose run --rm -it allure allure generate /allure-results -o /allure-report --clean"
    )
    c.run("docker compose restart allure")
    c.run("open -a 'Google Chrome' http://localhost:8800")


@task
def keygen(c: Context):
    """Generate SSL key and cert for localhost"""
    c.run("mkdir -p ssl_certs")
    c.run(
        "openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
        "-keyout ssl_certs/localhost.key -out ssl_certs/localhost.crt"
    )


@task
def mkcert(c: Context):
    """Generate SSL cert with mkcert"""
    c.run("mkdir -p ssl_certs")
    c.run(
        "mkcert -cert-file ssl_certs/localhost.crt "
        "-key-file ssl_certs/localhost.key lexiflux.ai localhost 127.0.0.1"
    )


@task
def docker(c: Context):
    """Build docker image"""
    c.run("docker build -t lexiflux:latest -f docker/Dockerfile .")


@task
def uv(c: Context):
    """Install or upgrade uv."""
    c.run("curl -LsSf https://astral.sh/uv/install.sh | sh")


@task
def pre(c):
    """Run pre-commit checks"""
    c.run("pre-commit run --verbose --all-files")


namespace = Collection.from_module(sys.modules[__name__])
for name in ALLOWED_VERSION_TYPES:
    namespace.add_task(ver_task_factory(name), name=f"ver-{name}")
for name in ALLOWED_DOC_LANGUAGES:
    namespace.add_task(docs_task_factory(name), name=f"docs-{name}")

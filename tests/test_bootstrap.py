from typer.testing import CliRunner

from apps.cli.main import app
from agentflow_studio import __version__


def test_version_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.output

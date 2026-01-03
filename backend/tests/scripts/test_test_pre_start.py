from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.tests_pre_start import init, logger


def test_init_successful_connection() -> None:
    engine_mock = MagicMock()

    session_mock = MagicMock()
    exec_mock = MagicMock(return_value=True)
    session_mock.configure_mock(**{"exec.return_value": exec_mock})
    # Set up context manager support
    session_mock.__enter__ = MagicMock(return_value=session_mock)
    session_mock.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.tests_pre_start.Session", return_value=session_mock),
        patch.object(logger, "info"),
        patch.object(logger, "error"),
        patch.object(logger, "warn"),
    ):
        try:
            init(engine_mock)
            connection_successful = True
        except Exception:
            connection_successful = False

        assert (
            connection_successful
        ), "The database connection should be successful and not raise an exception."

        assert (
            session_mock.exec.call_count == 1
        ), "The session should execute a select statement once."
        # Verify it was called with a select(1) query
        call_args = session_mock.exec.call_args[0][0]
        assert str(call_args) == str(select(1)), "Should execute select(1)"

from scripts.mysql_backup import derive_key, mysql_cli_args


def test_mysql_backup_cli_args_do_not_expose_password() -> None:
    args, password = mysql_cli_args(
        "mysql+pymysql://backup-user:test-secret@127.0.0.1:3307/mycmd_test"
    )
    assert password == "test-secret"
    assert not any("test-secret" in arg for arg in args)
    assert args == [
        "--host=127.0.0.1",
        "--port=3307",
        "--user=backup-user",
        "mycmd_test",
    ]


def test_mysql_backup_key_derivation_is_deterministic() -> None:
    salt = bytes(range(16))
    assert derive_key("test-key", salt) == derive_key("test-key", salt)

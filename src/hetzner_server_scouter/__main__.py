from hetzner_server_scouter.db.crud import download_server_list
from hetzner_server_scouter.db.db_conf import init_database, DatabaseSessionMaker
from hetzner_server_scouter.notify.crud import read_notification_config
from hetzner_server_scouter.utils import program_args, print_version


# TODO: Logs for what happened in the past
# TODO: Daily summary?

def main() -> None:
    init_database()

    if program_args.version:
        print_version()
        exit(0)

    with DatabaseSessionMaker() as db:
        config = read_notification_config(db)
        servers = download_server_list(db, config)

        _ = servers


if __name__ == "__main__":
    main()

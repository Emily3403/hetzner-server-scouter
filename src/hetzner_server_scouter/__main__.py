from hetzner_server_scouter.db.db_conf import init_database, DatabaseSessionMaker
from hetzner_server_scouter.utils import program_args, print_version


def main() -> None:
    init_database()

    if program_args.version:
        print_version()
        exit(0)

    with DatabaseSessionMaker() as db:
        _ = db
        pass


if __name__ == "__main__":
    main()
